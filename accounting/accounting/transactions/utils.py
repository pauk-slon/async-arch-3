from typing import Any, Mapping, Type, TypeVar

from sqlalchemy import select

from accounting.models import SQLModel

ModelT = TypeVar('ModelT', bound=SQLModel)


async def get_or_create(
    session,
    model: Type[ModelT],
    defaults: Mapping[str, Any] | None = None,
    **filter_kwargs: Any,
) -> (ModelT, bool):
    query_result = await session.execute(select(model).filter_by(**filter_kwargs))
    instance: model | None = query_result.scalar_one_or_none()
    created = False
    if not instance:
        instance_kwargs = defaults | filter_kwargs if defaults else filter_kwargs
        instance = model(**instance_kwargs)
        session.add(instance)
        created = True
    return instance, created
