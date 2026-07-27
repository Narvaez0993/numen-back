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

    async def top_merchants(
        self,
        user_id: UUID,
        date_from: str,
        date_to: str,
        category_id: str | None,
        limit: int,
    ) -> list[MerchantSpend]:
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    **self._range_match(user_id, date_from, date_to),
                    "type": "expense",
                    "category_id": category_id,
                }
            },
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
