from __future__ import annotations

import importlib.metadata
import re
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Union, cast

from sqlalchemy import inspect, inspection, tuple_
from sqlalchemy.orm import (
    DeclarativeMeta,
    Query,
    aliased,
    contains_eager,
    defaultload,
)

import graphene_sqlalchemy
from graphene.utils.str_converters import to_snake_case
from promise import Promise, dataloader


if TYPE_CHECKING:
    from collections.abc import Callable

    from graphene.relay import Connection
    from graphql import ResolveInfo

    from .filters import FilterSet

_gqls_version_match = re.match(
    r"(\d+)\.(\d+)\.(\d+)", importlib.metadata.version("graphene-sqlalchemy")
)
gqls_version = ()
if _gqls_version_match:
    gqls_version: tuple[int, ...] = tuple(
        int(x) for x in _gqls_version_match.groups()
    )


graphene_sqlalchemy_version_lt_2_1_2 = gqls_version < (2, 1, 2)
if graphene_sqlalchemy_version_lt_2_1_2:
    default_connection_field_factory = None
else:
    from graphene_sqlalchemy.fields import default_connection_field_factory


SqlaModel = Union[DeclarativeMeta, type[DeclarativeMeta]]

DEFAULT_FILTER_ARG: str = "filters"


class FilterableConnectionField(graphene_sqlalchemy.SQLAlchemyConnectionField):
    filter_arg: ClassVar[str] = DEFAULT_FILTER_ARG

    factory: ClassVar[FilterableFieldFactory | Callable | None] = None
    filters: ClassVar[dict] = {}

    def __init_subclass__(cls) -> None:
        if graphene_sqlalchemy_version_lt_2_1_2:
            return

        if cls.filters and cls.factory is None:
            cls.factory = FilterableFieldFactory(cls.filters)

            if cls.filter_arg != DEFAULT_FILTER_ARG:
                # Update filter arg for nested fields.
                cls.factory.model_loader_class = type(
                    "CustomModelLoader",
                    (ModelLoader,),
                    {"filter_arg": cls.filter_arg},
                )
        elif cls.factory is None:
            cls.factory = default_connection_field_factory

    def __init__(
        self, connection: type[Connection], *args: Any, **kwargs: Any
    ) -> None:
        if self.filter_arg not in kwargs:
            model = connection._meta.node._meta.model

            with suppress(KeyError):
                kwargs[self.filter_arg] = self.filters[model]

        super().__init__(connection, *args, **kwargs)

    @classmethod
    def get_query(
        cls, model: SqlaModel, info: ResolveInfo, sort: Any = None, **args: Any
    ) -> Query:
        """Standard get_query with filtering."""
        pass

    @classmethod
    def get_filter_set(cls, info: ResolveInfo) -> FilterSet:
        """Get field filter set.

        Args:
            info: Graphene resolve info object.

        Returns:
            FilterSet class from field args.

        """
        pass


class ModelLoader(dataloader.DataLoader):
    filter_arg: str = DEFAULT_FILTER_ARG

    def __init__(
        self,
        parent_model: Any,
        model: SqlaModel,
        info: ResolveInfo,
        graphql_args: dict,
    ) -> None:
        """Dataloader for SQLAlchemy model relations.

        Args:
            parent_model: Parent SQLAlchemy model.
            model: SQLAlchemy model.
            info: Graphene resolve info object.
            graphql_args: Request args: filters, sort, ...

        """
        super().__init__()
        self.info: ResolveInfo = info
        self.graphql_args: dict = graphql_args

        self.model: SqlaModel = model
        self.parent_model: Any = parent_model
        self.parent_model_pks: tuple[str, ...] = self._get_model_pks(
            self.parent_model
        )
        self.parent_model_pk_fields: tuple = tuple(
            getattr(self.parent_model, pk) for pk in self.parent_model_pks
        )

        self.model_relation_field: str = to_snake_case(self.info.field_name)

        self.relation: Any = getattr(
            self.parent_model, self.model_relation_field
        )

    def batch_load_fn(self, keys: list[tuple[Any]]) -> Promise:
        """Load related objects.

        Args:
            keys: Primary key values of parent model.

        Returns:
            Lists of related orm objects.

        """
        pass

    @staticmethod
    def _get_model_pks(model: SqlaModel) -> tuple[str, ...]:
        """Get primary key field name.

        Args:
            model: SQLAlchemy model.

        Returns:
            Field name.

        """
        pass

    def parent_model_object_to_key(self, parent_object: Any) -> Any:
        """Get primary key value from SQLAlchemy orm object.

        Args:
            parent_object: SQLAlchemy orm object.

        Returns:
            Primary key value.

        """
        pass

    @classmethod
    def _get_filter_set(cls, info: ResolveInfo) -> FilterSet:
        """Get field filter set.

        Args:
            info: Graphene resolve info object.

        Returns:
            FilterSet class from field args.

        """
        pass

    def _get_query(self) -> Query:
        """Build, filter and sort the query.

        Returns:
            SQLAlchemy query.

        """
        pass

    def _sorted_query(
        self, query: Query, sort: list | None, by_model: Any
    ) -> Query:
        """Sort query."""
        pass


class NestedFilterableConnectionField(FilterableConnectionField):
    dataloaders_field: str = "_sqla_filter_dataloaders"

    @classmethod
    def _get_or_create_data_loader(
        cls, root: Any, model: SqlaModel, info: ResolveInfo, args: dict
    ) -> ModelLoader:
        """Get or create (and save) dataloader from ResolveInfo.

        Args:
            root: Parent model orm object.
            model: SQLAlchemy model.
            info: Graphene resolve info object.
            args: Request args: filters, sort, ...

        Returns:
            Dataloader for SQLAlchemy model.

        """
        pass

    @classmethod
    def connection_resolver(
        cls,
        resolver: Any,  # noqa: ARG003
        connection_type: Any,
        model: SqlaModel,
        root: Any,
        info: ResolveInfo,
        **kwargs: dict,
    ) -> Promise | Connection:
        """Resolve nested connection.

        Args:
            resolver: Default resolver.
            connection_type: Connection class.
            model: SQLAlchemy model.
            root: Parent SQLAlchemy object.
            info: Graphene resolve info object.
            **kwargs: Request args: filters, sort, ...

        Returns:
            Connection object.

        """
        pass


class FilterableFieldFactory:
    model_loader_class: type[ModelLoader] = ModelLoader
    field_class: type[NestedFilterableConnectionField] = (
        NestedFilterableConnectionField
    )

    def __init__(self, model_filters: dict) -> None:
        self.model_filters: dict = model_filters

    def __call__(
        self, relationship: Any, registry: Any = None, **field_kwargs: dict
    ) -> NestedFilterableConnectionField:
        """Get field for relation.

        Args:
            relationship: SQLAlchemy relation.
            registry: graphene-sqlalchemy registry.
            **field_kwargs: Field args.

        Returns:
            Filed object.

        """
        model = relationship.mapper.entity
        model_type = registry.get_type_for_model(model)

        filters: FilterSet | None = self.model_filters.get(model)

        if filters is not None:
            field_kwargs.setdefault(
                self.model_loader_class.filter_arg, filters
            )

        return self.field_class(model_type._meta.connection, **field_kwargs)
