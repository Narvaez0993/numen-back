from typing import Any
from uuid import UUID

from src.modules.movements.adapters.outbound.persistence.documents.movement_document import (
    MovementDocument,
)
from src.modules.movements.adapters.outbound.persistence.mappers.movement_mapper import (
    MovementMapper,
)
from src.modules.movements.application.ports.movement_repository import (
    CategorySpend,
    DaySpend,
    DebtTransfer,
    GoalFunds,
    MerchantSpend,
    MovementQuery,
    MovementTotals,
)
from src.modules.movements.domain.entities.movement import Movement
from src.shared.adapters.outbound.persistence.mongo import current_session


class MongoMovementRepository:
    """Beanie/Mongo implementation of `MovementRepository`.

    Queries are always tenant-scoped and served by the compound index on
    `(user_id, occurred_on desc, created_at desc)` declared in `MovementDocument`,
    which also gives the listing its stable newest-first order.
    """

    async def search(self, query: MovementQuery) -> list[Movement]:
        criteria: dict[str, Any] = {"user_id": str(query.user_id)}

        date_bounds: dict[str, str] = {}
        if query.date_from is not None:
            date_bounds["$gte"] = query.date_from
        if query.date_to is not None:
            date_bounds["$lte"] = query.date_to
        if date_bounds:
            criteria["occurred_on"] = date_bounds

        if query.type is not None:
            criteria["type"] = query.type
        if query.category_id is not None:
            criteria["category_id"] = query.category_id
        if query.source_id is not None:
            # A source matches on either end of a transfer.
            criteria["$or"] = [
                {"source_id": query.source_id},
                {"destination_id": query.source_id},
            ]

        docs = (
            await MovementDocument.find(criteria)
            .sort("-occurred_on", "-created_at")
            .limit(query.limit)
            .to_list()
        )
        return [MovementMapper.to_domain(doc) for doc in docs]

    async def find(self, user_id: UUID, movement_id: str) -> Movement | None:
        doc = await MovementDocument.find_one(
            MovementDocument.id == movement_id,
            MovementDocument.user_id == str(user_id),
        )
        return MovementMapper.to_domain(doc) if doc else None

    async def save(self, movement: Movement) -> None:
        session = current_session()
        existing = await MovementDocument.get(movement.id, session=session)
        if existing is None:
            await MovementMapper.to_document(movement).insert(session=session)
            return
        existing.description = movement.description
        existing.amount = movement.amount
        existing.currency = movement.currency
        existing.source_type = movement.source.type
        existing.source_id = movement.source.id
        existing.destination_type = (
            movement.destination.type if movement.destination is not None else None
        )
        existing.destination_id = (
            movement.destination.id if movement.destination is not None else None
        )
        existing.category_id = movement.category_id
        existing.occurred_on = movement.occurred_on
        await existing.save(session=session)

    async def delete(self, user_id: UUID, movement_id: str) -> None:
        doc = await MovementDocument.find_one(
            MovementDocument.id == movement_id,
            MovementDocument.user_id == str(user_id),
        )
        if doc is not None:
            await doc.delete(session=current_session())

    @staticmethod
    def _range_match(user_id: UUID, date_from: str, date_to: str) -> dict[str, Any]:
        """The `$match` every aggregation starts with — and the prefix of
        `ix_user_created`, so the index does the narrowing."""
        return {
            "user_id": str(user_id),
            "occurred_on": {"$gte": date_from, "$lte": date_to},
        }

    async def totals(self, user_id: UUID, date_from: str, date_to: str) -> MovementTotals:
        pipeline: list[dict[str, Any]] = [
            {"$match": self._range_match(user_id, date_from, date_to)},
            {
                "$group": {
                    "_id": "$type",
                    "total": {"$sum": "$amount"},
                    "count": {"$sum": 1},
                }
            },
        ]
        rows = await MovementDocument.aggregate(pipeline).to_list()
        by_type = {row["_id"]: row for row in rows}
        expense = by_type.get("expense", {})
        income = by_type.get("income", {})
        return MovementTotals(
            expense_total=int(expense.get("total", 0)),
            income_total=int(income.get("total", 0)),
            # Transfers count as movements even though they are neither total.
            count=sum(int(row["count"]) for row in rows),
        )

    async def spend_by_category(
        self, user_id: UUID, date_from: str, date_to: str
    ) -> list[CategorySpend]:
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    **self._range_match(user_id, date_from, date_to),
                    "type": "expense",
                }
            },
            {
                "$group": {
                    "_id": "$category_id",
                    "spent": {"$sum": "$amount"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"spent": -1}},
        ]
        rows = await MovementDocument.aggregate(pipeline).to_list()
        return [
            CategorySpend(
                category_id=row["_id"],
                spent=int(row["spent"]),
                count=int(row["count"]),
            )
            for row in rows
        ]

    async def spend_by_day(self, user_id: UUID, date_from: str, date_to: str) -> list[DaySpend]:
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    **self._range_match(user_id, date_from, date_to),
                    "type": "expense",
                }
            },
            {
                "$group": {
                    "_id": "$occurred_on",
                    "spent": {"$sum": "$amount"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        rows = await MovementDocument.aggregate(pipeline).to_list()
        return [
            DaySpend(
                day=str(row["_id"]),
                spent=int(row["spent"]),
                count=int(row["count"]),
            )
            for row in rows
        ]

    async def top_merchants(
        self,
        user_id: UUID,
        date_from: str,
        date_to: str,
        category_id: str | None,
        limit: int,
    ) -> list[MerchantSpend]:
        return await self._merchants(
            {
                **self._range_match(user_id, date_from, date_to),
                "type": "expense",
                "category_id": category_id,
            },
            limit,
        )

    async def top_merchants_overall(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> list[MerchantSpend]:
        # No category in the match: this one ranks the whole period's expenses.
        return await self._merchants(
            {**self._range_match(user_id, date_from, date_to), "type": "expense"},
            limit,
        )

    @staticmethod
    async def _merchants(match: dict[str, Any], limit: int) -> list[MerchantSpend]:
        pipeline: list[dict[str, Any]] = [
            {"$match": match},
            # Newest first, so `$first` below picks the spelling the user typed last.
            {"$sort": {"occurred_on": -1}},
            {
                "$group": {
                    "_id": {"$toLower": {"$trim": {"input": "$description"}}},
                    "label": {"$first": "$description"},
                    "spent": {"$sum": "$amount"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"spent": -1}},
            {"$limit": limit},
        ]
        rows = await MovementDocument.aggregate(pipeline).to_list()
        return [
            MerchantSpend(
                label=str(row["label"]).strip(),
                spent=int(row["spent"]),
                count=int(row["count"]),
            )
            for row in rows
        ]

    async def goal_funds(self, user_id: UUID) -> list[GoalFunds]:
        incoming = await MovementDocument.aggregate(
            [
                {
                    "$match": {
                        "user_id": str(user_id),
                        "type": "transfer",
                        "destination_type": "goal",
                    }
                },
                {
                    "$group": {
                        "_id": "$destination_id",
                        "total": {"$sum": "$amount"},
                        "first_on": {"$min": "$occurred_on"},
                    }
                },
            ]
        ).to_list()
        outgoing = await MovementDocument.aggregate(
            [
                {
                    "$match": {
                        "user_id": str(user_id),
                        "type": "transfer",
                        "source_type": "goal",
                    }
                },
                {"$group": {"_id": "$source_id", "total": {"$sum": "$amount"}}},
            ]
        ).to_list()

        withdrawn = {row["_id"]: int(row["total"]) for row in outgoing}
        funds = {
            row["_id"]: GoalFunds(
                goal_id=row["_id"],
                saved=int(row["total"]) - withdrawn.pop(row["_id"], 0),
                first_in_on=row["first_on"],
            )
            for row in incoming
        }
        # A pocket someone only ever withdrew from (contributions deleted, say) still
        # has to report — as zero-or-negative funds the caller can see, not silence.
        for goal_id, total in withdrawn.items():
            funds[goal_id] = GoalFunds(goal_id=goal_id, saved=-total, first_in_on=None)
        return list(funds.values())

    async def debt_transfers(self, user_id: UUID) -> list[DebtTransfer]:
        """A plain read, not an aggregation: the caller wants the instalments, and a
        person's debt movements are dozens, not thousands.

        Not filtered by type: the write-off is an expense out of the debt, and the
        caller needs to tell it apart rather than never see it.
        """
        docs = await MovementDocument.find(
            MovementDocument.user_id == str(user_id),
            {"$or": [{"source_type": "debt"}, {"destination_type": "debt"}]},
        ).to_list()
        rows = [
            DebtTransfer(
                # One end is always the debt (the filter guarantees it), and the
                # id beside a `debt` type is never null.
                debt_id=str(
                    doc.destination_id if doc.destination_type == "debt" else doc.source_id
                ),
                movement_id=doc.id,
                amount=doc.amount,
                occurred_on=doc.occurred_on,
                description=doc.description,
                into_debt=doc.destination_type == "debt",
                movement_type=doc.type,
            )
            for doc in docs
            # A transfer between two debts cannot exist (validation forbids it), but
            # reading defensively costs nothing and a mis-keyed row would be silent.
            if doc.source_type == "debt" or doc.destination_type == "debt"
        ]
        rows.sort(key=lambda row: (row.occurred_on, row.movement_id))
        return rows
