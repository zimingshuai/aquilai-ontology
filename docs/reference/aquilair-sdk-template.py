
from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields as dataclass_fields
from datetime import date, datetime
from functools import wraps
import os
from typing import (
    Any,
    ClassVar,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)


# ---------------------------------------------------------------------------
# 实体模型（由 metadata-service 按当前工作区生成）
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# 基础返回类型
# ---------------------------------------------------------------------------


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """实体 load 接口返回的一页数据。"""

    data: list[T]
    next_page_token: str | None = None
    total_count: int | None = None


# ---------------------------------------------------------------------------
# 字段和关系元数据
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldRef:
    """字段引用，用于 where、select 和排序。"""

    field_name: str

    def __repr__(self) -> str:
        return f"FieldRef({self.field_name!r})"

    def eq(self, value: Any) -> WhereExpression:
        return _Comparison("eq", self, value)

    def neq(self, value: Any) -> WhereExpression:
        return _Comparison("neq", self, value)

    def lt(self, value: Any) -> WhereExpression:
        return _Comparison("lt", self, value)

    def lte(self, value: Any) -> WhereExpression:
        return _Comparison("lte", self, value)

    def gt(self, value: Any) -> WhereExpression:
        return _Comparison("gt", self, value)

    def gte(self, value: Any) -> WhereExpression:
        return _Comparison("gte", self, value)

    def between(self, minimum: Any, maximum: Any) -> WhereExpression:
        return _Comparison("between", self, {"min": minimum, "max": maximum})

    def in_(self, values: Sequence[Any]) -> WhereExpression:
        if isinstance(values, (str, bytes)):
            raise TypeError("in_ expects a sequence of values, not a string")
        return _Comparison("in", self, list(values))

    def is_null(self) -> WhereExpression:
        return _NullCheck("isNull", self)

    def is_not_null(self) -> WhereExpression:
        return _NullCheck("isNotNull", self)

    def contains_any_term(self, value: str) -> WhereExpression:
        return _Comparison("containsAnyTerm", self, value)

    def contains_all_terms(self, value: str) -> WhereExpression:
        return _Comparison("containsAllTerms", self, value)

    def contains_all_terms_in_order(self, value: str) -> WhereExpression:
        return _Comparison("containsAllTermsInOrder", self, value)

    def asc(self) -> SortField:
        return SortField(self, "asc")

    def desc(self) -> SortField:
        return SortField(self, "desc")




@dataclass(frozen=True)
class _ObjectDefinition:
    """一个实体的对象类型 code、Python 模型和主键等生成元数据。"""

    entity_name: str
    object_code: str
    model_type: type[Any]
    primary_key_field: str
    fields_by_name: Mapping[str, FieldRef]


def _make_definition(
    entity_name: str,
    object_code: str,
    model_type: type[Any],
    primary_key_field: str,
) -> _ObjectDefinition:
    """从 dataclass 和公开的 ``fields`` 字段引用生成实体定义。"""

    names = {field.name for field in dataclass_fields(model_type)}
    fields_by_name = {
        name: cast(FieldRef, getattr(model_type.fields, name))
        for name in names
    }
    return _ObjectDefinition(
        entity_name=entity_name,
        object_code=object_code,
        model_type=model_type,
        primary_key_field=primary_key_field,
        fields_by_name=fields_by_name,
    )



OBJECT_DEFINITIONS: dict[str, _ObjectDefinition] = {
}

OBJECT_DEFINITIONS_BY_CODE: dict[str, _ObjectDefinition] = {
    definition.object_code: definition
    for definition in OBJECT_DEFINITIONS.values()
}

@dataclass(frozen=True)
class RelationDefinition:
    """一个对象关系及其正反向访问名称。"""

    code: str
    source_object: str
    source_field: str
    target_object: str
    target_field: str
    cardinality: Cardinality
    source_name: str
    target_name: str

    def returns_many(self, side: Literal["source", "target"]) -> bool:
        """判断从关系一端访问另一端时是否返回列表。"""

        return (
            self.cardinality == "N:N"
            or (self.cardinality == "1:N" and side == "source")
            or (self.cardinality == "N:1" and side == "target")
        )


Cardinality = Literal["1:1", "1:N", "N:1", "N:N"]

RELATION_DEFINITIONS: dict[str, RelationDefinition] = {
}

class _RelationAccessor:
    """在实体实例上按点号访问关联对象。"""

    def __init__(
        self,
        relation: RelationDefinition,
        side: Literal["source", "target"],
    ) -> None:
        self._relation = relation
        self._side = side

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        if instance is None:
            return self
        client = getattr(instance, "_dataservice_client", None)
        if client is None:
            raise RuntimeError(
                "related objects are available only on objects loaded by WorkspaceClient"
            )

        owner_object = (
            self._relation.source_object
            if self._side == "source"
            else self._relation.target_object
        )
        owner_definition = OBJECT_DEFINITIONS[owner_object]
        primary_key = getattr(instance, owner_definition.primary_key_field, None)
        if primary_key is None:
            return [] if self._relation.returns_many(self._side) else None

        related = (
            EntityEndpoint(client, owner_definition)
            .static([str(primary_key)])
            .search_around(self._relation.code)
            .load()
            .data
        )
        if self._relation.returns_many(self._side):
            return related
        if len(related) > 1:
            raise DataServiceError(
                f"relation {self._relation.code} expected one related object"
            )
        return related[0] if related else None


for _relation in RELATION_DEFINITIONS.values():
    _source_definition = OBJECT_DEFINITIONS[_relation.source_object]
    _target_definition = OBJECT_DEFINITIONS[_relation.target_object]
    setattr(
        _source_definition.model_type,
        _relation.source_name,
        _RelationAccessor(_relation, "source"),
    )
    setattr(
        _target_definition.model_type,
        _relation.target_name,
        _RelationAccessor(_relation, "target"),
    )


# ---------------------------------------------------------------------------
# ObjectSet 和 where 表达式（新增的标准查询能力）
# ---------------------------------------------------------------------------


class WhereExpression:
    """标准 ObjectSet ``where`` 表达式的基类。"""

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def __and__(self, other: WhereExpression) -> WhereExpression:
        return _Logical("and", [self, other])

    def __or__(self, other: WhereExpression) -> WhereExpression:
        return _Logical("or", [self, other])

    def __invert__(self) -> WhereExpression:
        return _Not(self)

    def and_(self, *others: WhereExpression) -> WhereExpression:
        """用显式方法连接条件，避免依赖 Python 的 ``&`` 运算符。"""

        return and_(self, *others)

    def or_(self, *others: WhereExpression) -> WhereExpression:
        """用显式方法连接条件，避免依赖 Python 的 ``|`` 运算符。"""

        return or_(self, *others)

    def not_(self) -> WhereExpression:
        """返回当前条件的逻辑否定。"""

        return _Not(self)

    def __bool__(self) -> bool:
        raise TypeError("ObjectSet where expressions cannot be used as booleans")


@dataclass(frozen=True)
class _Comparison(WhereExpression):
    operator: str
    field: FieldRef
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.operator,
            "field": self.field.field_name,
            "value": self.value,
        }


@dataclass(frozen=True)
class _NullCheck(WhereExpression):
    operator: str
    field: FieldRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.operator,
            "field": self.field.field_name,
        }


@dataclass(frozen=True)
class _Logical(WhereExpression):
    operator: str
    children: Sequence[WhereExpression]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.operator,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True)
class _Not(WhereExpression):
    child: WhereExpression

    def to_dict(self) -> dict[str, Any]:
        return {"type": "not", "child": self.child.to_dict()}


@dataclass(frozen=True)
class SortField:
    field: FieldRef
    direction: Literal["asc", "desc"] = "asc"

    def to_dict(self) -> dict[str, str]:
        return {
            "field": self.field.field_name,
            "direction": self.direction,
        }


def _as_where(value: WhereExpression | Mapping[str, Any]) -> dict[str, Any]:
    """将类型化条件或原始 JSON 条件统一转换为请求字典。"""

    if isinstance(value, WhereExpression):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("where must be a WhereExpression or an ObjectSet where object")


def and_(*expressions: WhereExpression) -> WhereExpression:
    """显式构造 ``and`` 条件；名称末尾的下划线是 Python 关键字约束。"""

    if not expressions:
        raise ValueError("and_ requires at least one expression")
    if not all(isinstance(expression, WhereExpression) for expression in expressions):
        raise TypeError("and_ arguments must be WhereExpression instances")
    return _Logical("and", list(expressions))


def or_(*expressions: WhereExpression) -> WhereExpression:
    """显式构造 ``or`` 条件；名称末尾的下划线是 Python 关键字约束。"""

    if not expressions:
        raise ValueError("or_ requires at least one expression")
    if not all(isinstance(expression, WhereExpression) for expression in expressions):
        raise TypeError("or_ arguments must be WhereExpression instances")
    return _Logical("or", list(expressions))


def not_(expression: WhereExpression) -> WhereExpression:
    """显式构造 ``not`` 条件。"""

    if not isinstance(expression, WhereExpression):
        raise TypeError("not_ argument must be a WhereExpression instance")
    return _Not(expression)


def _field_for(
    definition: _ObjectDefinition | None, value: FieldRef | str
) -> FieldRef:
    """解析字段引用；关系跳转结果尚未加载时允许原始字段名。"""

    if isinstance(value, FieldRef):
        if definition is None:
            return value
        if value in definition.fields_by_name.values():
            return value
        field_name = value.field_name
    else:
        field_name = value

    if not isinstance(field_name, str):
        raise TypeError("field must be a FieldRef or string")
    if definition is None:
        return FieldRef(field_name)
    if field_name in definition.fields_by_name:
        return definition.fields_by_name[field_name]
    raise ValueError(f"unknown field for {definition.entity_name}: {field_name!r}")


def _select_fields(
    definition: _ObjectDefinition | None,
    select: Sequence[FieldRef | str] | None,
) -> list[str] | None:
    """校验并序列化 ``select``；字段名按 DataService 原样发送。"""

    if select is None:
        return None
    if isinstance(select, (str, bytes)):
        raise TypeError("select must be a sequence of fields")
    values = [_field_for(definition, item).field_name for item in select]
    if not values:
        raise ValueError("select must contain at least one field")
    return values


def _parse_direction(value: Any) -> Literal["asc", "desc"]:
    """校验并返回标准化后的排序方向。"""

    direction = str(value).lower()
    if direction not in {"asc", "desc"}:
        raise ValueError("order_by direction must be asc or desc")
    return cast(Literal["asc", "desc"], direction)


def _serialize_order_by(
    definition: _ObjectDefinition | None,
    order_by: str | SortField | FieldRef | Mapping[str, Any] | Sequence[Any] | None,
) -> dict[str, Any] | None:
    """将多种便捷排序写法统一转换成 ObjectSet ``orderBy`` JSON。"""

    if order_by is None:
        return None
    if isinstance(order_by, SortField):
        fields = [order_by]
    elif isinstance(order_by, FieldRef):
        fields = [SortField(order_by)]
    elif isinstance(order_by, str):
        fields = [SortField(_field_for(definition, order_by))]
    elif isinstance(order_by, Mapping):
        if order_by.get("type") == "relevance":
            return {"type": "relevance"}
        if "fields" in order_by:
            raw_fields = order_by["fields"]
            if not isinstance(raw_fields, Sequence) or isinstance(raw_fields, (str, bytes)):
                raise ValueError("order_by.fields must be a sequence")
            fields = list(raw_fields)
        elif "field" in order_by:
            field = order_by["field"]
            fields = [
                SortField(
                    _field_for(definition, cast(FieldRef | str, field)),
                    _parse_direction(order_by.get("direction", "asc")),
                )
            ]
        else:
            fields = [
                SortField(_field_for(definition, field), _parse_direction(direction))
                for field, direction in order_by.items()
            ]
    else:
        if isinstance(order_by, (str, bytes)):
            raise TypeError("order_by must be a SortField or sequence")
        fields = list(cast(Sequence[Any], order_by))

    result: list[dict[str, str]] = []
    for item in fields:
        if isinstance(item, FieldRef):
            item = SortField(item)
        if isinstance(item, Mapping):
            field_value = item.get("field")
            item = SortField(
                _field_for(definition, cast(FieldRef | str, field_value)),
                _parse_direction(item.get("direction", "asc")),
            )
        if not isinstance(item, SortField):
            raise TypeError("each order_by value must be a SortField")
        result.append(item.to_dict())
    if not result:
        raise ValueError("order_by must contain at least one field")
    return {"type": "fields", "fields": result}

# ---------------------------------------------------------------------------
# 响应模型解码
# ---------------------------------------------------------------------------


def _decode_model(
    definition: _ObjectDefinition,
    payload: Mapping[str, Any],
    client: Any | None = None,
) -> Any:
    """将 DataService 对象响应解码为对应的实体 dataclass。"""

    properties = payload.get("properties")
    if not isinstance(properties, Mapping):
        raise DataServiceError("DataService returned invalid properties")

    type_hints = get_type_hints(definition.model_type)
    values: dict[str, Any] = {}
    for field in dataclass_fields(definition.model_type):
        property_ref = definition.fields_by_name[field.name].field_name
        if property_ref not in properties:
            continue
        value = properties[property_ref]
        annotation = type_hints.get(field.name)
        possible_types = set(get_args(annotation)) if annotation else set()
        if annotation is datetime or datetime in possible_types:
            if isinstance(value, str):
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif annotation is date or date in possible_types:
            if isinstance(value, str):
                value = date.fromisoformat(value)
        elif annotation is float or float in possible_types:
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError as error:
                    raise DataServiceError(
                        f"DataService returned invalid numeric property: {property_ref!r}"
                    ) from error
        elif annotation is int or int in possible_types:
            if isinstance(value, str):
                try:
                    value = int(value)
                except ValueError as error:
                    raise DataServiceError(
                        f"DataService returned invalid integer property: {property_ref!r}"
                    ) from error
        values[field.name] = value

    primary_key = definition.primary_key_field
    if primary_key not in values and payload.get("id") is not None:
        values[primary_key] = payload["id"]
    model = definition.model_type(**values)
    if client is not None:
        object.__setattr__(model, "_dataservice_client", client)
    return model


class ObjectSet(Generic[T]):
    """由标准 load 接口执行的不可变 ObjectSet 构造器。"""

    def __init__(
        self,
        client: _HttpClient,
        definition: _ObjectDefinition | None,
        node: Mapping[str, Any],
    ) -> None:
        # 每个查询变换都创建新的 ObjectSet，因此调用方可以安全复用原查询。
        self._client = client
        self._definition = definition
        self._node = dict(node)

    @property
    def object_type(self) -> str | None:
        """返回当前 ObjectSet 的对象类型 code（关系跳转结果可能未知）。"""

        if self._definition is None:
            return None
        return self._definition.object_code

    def where(self, expression: WhereExpression | Mapping[str, Any]) -> ObjectSet[T]:
        """在当前 ObjectSet 上追加一个 filter 节点。"""

        return ObjectSet(
            self._client,
            self._definition,
            {
                "type": "filter",
                "objectSet": self._node,
                "where": _as_where(expression),
            },
        )

    def search_around(self, link_code: str) -> ObjectSet[Any]:
        """按 ``metadata_dev.link_types.code`` 沿关系查询另一端对象。"""

        if not isinstance(link_code, str) or not link_code:
            raise TypeError("search_around expects a non-empty link code string")
        # 关系方向、目标实体和关联字段由 DataService 元数据解析，SDK 只发送 code。
        return ObjectSet(
            self._client,
            None,
            {
                "type": "searchAround",
                "objectSet": self._node,
                "link": link_code,
            },
        )

    def union(self, *others: ObjectSet[T]) -> ObjectSet[T]:
        """构造多个同类型 ObjectSet 的并集。"""

        object_sets = (self, *others)
        self._require_same_type(object_sets, "union")
        return ObjectSet(
            self._client,
            self._definition,
            {"type": "union", "objectSets": [item._node for item in object_sets]},
        )

    def intersect(self, *others: ObjectSet[T]) -> ObjectSet[T]:
        """构造多个同类型 ObjectSet 的交集。"""

        object_sets = (self, *others)
        self._require_same_type(object_sets, "intersect")
        return ObjectSet(
            self._client,
            self._definition,
            {"type": "intersect", "objectSets": [item._node for item in object_sets]},
        )

    def subtract(self, other: ObjectSet[T]) -> ObjectSet[T]:
        """从当前 ObjectSet 中排除另一个同类型 ObjectSet。"""

        self._require_same_type((self, other), "subtract")
        return ObjectSet(
            self._client,
            self._definition,
            {"type": "subtract", "left": self._node, "right": other._node},
        )

    @staticmethod
    def _require_same_type(
        object_sets: Sequence[ObjectSet[Any]],
        operation: str,
    ) -> None:
        for item in object_sets:
            if not isinstance(item, ObjectSet):
                raise TypeError(f"{operation} operands must be ObjectSet instances")
        if any(item.object_type != object_sets[0].object_type for item in object_sets[1:]):
            raise ValueError(f"{operation} requires ObjectSets of the same type")

    def load(
        self,
        *,
        select: Sequence[FieldRef | str] | None = None,
        order_by: str | SortField | FieldRef | Mapping[str, Any] | Sequence[Any] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        snapshot: bool = False,
        include_total_count: bool = False,
        branch: str | None = None,
    ) -> Page[T]:
        """执行 ObjectSet 查询并返回当前页、下一页 token 和可选总数。"""

        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        body: dict[str, Any] = {
            "objectSet": self._node,
            "pageSize": page_size,
            "snapshot": snapshot,
            "includeTotalCount": include_total_count,
        }
        if select is not None:
            body["select"] = _select_fields(self._definition, select)
        if order_by is not None:
            body["orderBy"] = _serialize_order_by(self._definition, order_by)
        if page_token is not None:
            body["pageToken"] = page_token
        if branch is not None:
            body["branch"] = branch

        response = self._client.request(
            "POST",
            f"/v1/api/ontology/data/projects/"
            f"{quote(self._client.workspace_id, safe='')}/objectSets/loadObjects",
            body,
            operation=(
                f"{self._definition.entity_name}.load"
                if self._definition is not None
                else "ObjectSet.searchAround.load"
            ),
        )
        rows = response.get("records")
        if not isinstance(rows, list):
            raise DataServiceError("DataService returned invalid data.records")
        raw_total_count = response.get("totalCount")
        if raw_total_count is None:
            total_count = None
        elif isinstance(raw_total_count, str):
            try:
                total_count = int(raw_total_count)
            except ValueError as error:
                raise DataServiceError("DataService returned invalid totalCount") from error
        else:
            raise DataServiceError("DataService returned invalid totalCount")
        next_page_token = response.get("nextPageToken")
        if next_page_token is not None and not isinstance(next_page_token, str):
            raise DataServiceError("DataService returned invalid nextPageToken")
        decoded_rows: list[Any] = []
        for row in rows:
            definition = self._definition
            if definition is None:
                object_code = row.get("objectType")
                definition = OBJECT_DEFINITIONS_BY_CODE.get(object_code)
                if definition is None:
                    raise DataServiceError(
                        f"DataService returned unknown objectType: {object_code!r}"
                    )
            decoded_rows.append(_decode_model(definition, row, self._client))
        return Page(
            data=decoded_rows,
            next_page_token=next_page_token,
            total_count=cast(int | None, total_count),
        )


def _encode_change_value(value: Any) -> Any:
    """把 changes 里的日期时间值递归转成 ISO 字符串，保证结果可直接 ``json.dumps``。"""

    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _encode_change_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_change_value(item) for item in value]
    return value


@dataclass(frozen=True)
class OntologyEdit:
    """一条符合 DataService edits 入参契约的对象编辑项。"""

    object_type: str
    primary_key: str
    changes: Mapping[str, Any]
    operation: Literal["CREATE", "UPDATE", "DELETE"] = "UPDATE"

    def to_dict(self) -> dict[str, Any]:
        """返回可直接提交给 DataService 的编辑项。

        changes 中的日期和日期时间值会转成 ISO 8601 字符串，因此返回值
        可以直接传给 ``json.dumps``。
        """

        return {
            "operation": self.operation,
            "objectType": self.object_type,
            "primaryKey": self.primary_key,
            "changes": {
                key: _encode_change_value(value)
                for key, value in self.changes.items()
            },
        }


class EditableObject(Generic[T]):
    """Ontology edits 容器中的可编辑对象视图。

    该对象不复制完整实体，只记录调用方赋值过的字段；赋值不会立即发 HTTP，
    由所属的 :class:`OntologyEdits` 容器统一通过 ``get_edits`` 返回。
    """

    def __init__(
        self,
        endpoint: EntityEndpoint[T],
        primary_key: str,
        source: T | None = None,
        operation: Literal["CREATE", "UPDATE", "DELETE"] = "UPDATE",
    ) -> None:
        self._endpoint = endpoint
        self._primary_key = primary_key
        self._source = source
        self._operation = operation
        self._changes: dict[str, Any] = {}

    def __setattr__(self, name: str, value: Any) -> None:
        """把实体字段赋值转换为待应用变更。"""

        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        definition = self._endpoint._definition
        if self._operation == "DELETE":
            raise ValueError("a deleted object cannot be updated")
        if name == definition.primary_key_field:
            raise ValueError("an existing object's primary key cannot be updated")
        if name not in definition.fields_by_name:
            raise AttributeError(name)
        self._changes[name] = value

    def __getattr__(self, name: str) -> Any:
        """优先返回本次编辑后的值；有原对象时回退读取原值。"""

        if name in self._changes:
            return self._changes[name]
        if self._source is not None and name in self._endpoint._definition.fields_by_name:
            return getattr(self._source, name)
        raise AttributeError(name)

    @property
    def primary_key(self) -> str:
        """返回本次编辑对应的对象主键。"""

        return self._primary_key

    @property
    def has_changes(self) -> bool:
        """表示当前视图是否产生了一条 create/update/delete 意图。"""

        return self._operation != "UPDATE" or bool(self._changes)

    def _to_edit(self) -> OntologyEdit:
        """生成当前可编辑视图对应的待应用记录。"""

        definition = self._endpoint._definition
        changes = {
            definition.fields_by_name[name].field_name: value
            for name, value in self._changes.items()
        }
        return OntologyEdit(
            object_type=definition.object_code,
            primary_key=self._primary_key,
            changes=changes,
            operation=self._operation,
        )

    def _mark_deleted(self) -> None:
        self._operation = "DELETE"
        self._changes.clear()


class EntityEndpoint(Generic[T]):
    """实体查询接口；对象更新通过 ``client.edits()`` 进入。"""

    def __init__(self, client: _HttpClient, definition: _ObjectDefinition) -> None:
        self._client = client
        self._definition = definition

    def _base_object_set(self) -> ObjectSet[T]:
        """创建当前实体的 base ObjectSet 节点。"""

        return ObjectSet(
            self._client,
            self._definition,
            {"type": "base", "objectType": self._definition.object_code},
        )

    def where(self, expression: WhereExpression | Mapping[str, Any]) -> ObjectSet[T]:
        """从当前实体入口开始构造一个过滤查询。"""

        return self._base_object_set().where(expression)

    def static(self, objects: Sequence[str]) -> ObjectSet[T]:
        """构造由主键组成的 static ObjectSet。"""

        if isinstance(objects, (str, bytes)):
            raise TypeError("static expects a sequence of object IDs")
        return ObjectSet(
            self._client,
            self._definition,
            {
                "type": "static",
                "objectType": self._definition.object_code,
                "objects": list(objects),
            },
        )

    def detail(
        self,
        primary_key: str,
        *,
        select: Sequence[FieldRef | str] | None = None,
        branch: str | None = None,
    ) -> T:
        """按主键读取一个对象详情。"""

        fields = _select_fields(self._definition, select)
        path = (
            f"/v1/api/ontology/data/projects/{quote(self._client.workspace_id, safe='')}/objects/"
            f"{quote(self._definition.object_code, safe='')}/{quote(primary_key, safe='')}"
        )
        query: list[tuple[str, str]] = []
        if fields:
            query.extend(("select", value) for value in fields)
        if branch is not None:
            query.append(("branch", branch))
        if query:
            path = f"{path}?{urlencode(query)}"
        response = self._client.request(
            "GET",
            path,
            operation=f"{self._definition.entity_name}.detail",
        )
        return _decode_model(self._definition, response, self._client)

    def load(
        self,
        *,
        where: WhereExpression | Mapping[str, Any] | None = None,
        select: Sequence[FieldRef | str] | None = None,
        order_by: str | SortField | FieldRef | Mapping[str, Any] | Sequence[Any] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        snapshot: bool = False,
        include_total_count: bool = False,
        branch: str | None = None,
    ) -> Page[T]:
        """执行当前实体的 base/filter 查询。"""

        query = self._base_object_set()
        if where is not None:
            query = query.where(where)
        return query.load(
            select=select,
            order_by=order_by,
            page_size=page_size,
            page_token=page_token,
            snapshot=snapshot,
            include_total_count=include_total_count,
            branch=branch,
        )


class _EditEntityEndpoint(Generic[T]):
    """Ontology edits 容器中的实体编辑入口。"""

    def __init__(self, edits: OntologyEdits, endpoint: EntityEndpoint[T]) -> None:
        self._edits = edits
        self._endpoint = endpoint

    def edit(self, object_or_primary_key: T | str) -> EditableObject[T]:
        """按实体实例或主键创建可编辑对象视图。"""

        return self._edits._register(self._endpoint, object_or_primary_key, "UPDATE")

    def create(self, primary_key: str, **properties: Any) -> EditableObject[T]:
        """登记一个 CREATE 意图；属性只写入 edits 容器，不发 HTTP。"""

        editable = self._edits._register(self._endpoint, primary_key, "CREATE")
        for name, value in properties.items():
            setattr(editable, name, value)
        return editable

    def delete(self, object_or_primary_key: T | str | EditableObject[T]) -> None:
        """登记一个 DELETE 意图；删除只在 Action Runtime 真正发生。"""

        self._edits._delete(self._endpoint, object_or_primary_key)


class OntologyEdits:
    """收集多个对象修改的 edits 容器。

    ``get_edits`` 只返回待应用意图，不发 HTTP；真正写回由 Action Runtime 负责。
    """

    def __init__(self, client: _HttpClient) -> None:
        self._client = client
        self._endpoints: dict[str, EntityEndpoint[Any]] = {
            definition.entity_name: EntityEndpoint(client, definition)
            for definition in OBJECT_DEFINITIONS.values()
        }
        self._editable_objects: dict[tuple[str, str], EditableObject[Any]] = {}
        # 为编辑器提供 ``edits.objects.<Entity>.edit(...)`` 的补全信息。
        self.objects: _EditObjectsRuntime = _EditObjectsRuntime(self)

    def _register(
        self,
        endpoint: EntityEndpoint[T],
        object_or_primary_key: T | str,
        operation: Literal["CREATE", "UPDATE", "DELETE"] = "UPDATE",
    ) -> EditableObject[T]:
        """登记对象意图，并合并同一对象的重复编辑入口。"""

        definition = endpoint._definition
        primary_key, source = self._resolve_primary_key(endpoint, object_or_primary_key)

        identity = (definition.entity_name, primary_key)
        existing = self._editable_objects.get(identity)
        if existing is not None:
            if operation == "CREATE" and existing._operation != "CREATE":
                raise ValueError("cannot create an existing edited object")
            if operation == "UPDATE" and existing._operation == "DELETE":
                raise ValueError("cannot edit a deleted object")
            return cast(EditableObject[T], existing)
        editable = EditableObject(endpoint, primary_key, source, operation)
        self._editable_objects[identity] = editable
        return editable

    @staticmethod
    def _resolve_primary_key(
        endpoint: EntityEndpoint[T],
        object_or_primary_key: Any,
    ) -> tuple[str, Any]:
        definition = endpoint._definition
        if isinstance(object_or_primary_key, str):
            return object_or_primary_key, None
        if isinstance(object_or_primary_key, EditableObject):
            if object_or_primary_key._endpoint is not endpoint:
                raise ValueError("the editable object belongs to another edits container")
            return object_or_primary_key.primary_key, object_or_primary_key._source
        if isinstance(object_or_primary_key, definition.model_type):
            raw_primary_key = getattr(object_or_primary_key, definition.primary_key_field)
            if raw_primary_key is None:
                raise ValueError("an editable object must have a primary key")
            return str(raw_primary_key), object_or_primary_key
        raise TypeError("expected an entity instance or primary key")

    def _delete(
        self,
        endpoint: EntityEndpoint[T],
        object_or_primary_key: T | str | EditableObject[T],
    ) -> None:
        """登记删除，并按对象主键折叠同一容器中的前序意图。"""

        primary_key, source = self._resolve_primary_key(endpoint, object_or_primary_key)
        identity = (endpoint._definition.entity_name, primary_key)
        existing = self._editable_objects.get(identity)
        if existing is not None and existing._operation == "CREATE":
            del self._editable_objects[identity]
            return
        if existing is not None:
            existing._mark_deleted()
            return
        self._editable_objects[identity] = EditableObject(
            endpoint,
            primary_key,
            source,
            "DELETE",
        )

    def get_edits(self) -> list[OntologyEdit]:
        """返回待应用的编辑项，不发起 HTTP 请求。"""

        return [
            editable._to_edit()
            for editable in self._editable_objects.values()
            if editable.has_changes
        ]


class _EditObjectsRuntime:
    """将 edits 容器绑定成 edits.objects.<Entity> 编辑入口。"""



    def __init__(self, edits: OntologyEdits) -> None:
        for entity_name, endpoint in edits._endpoints.items():
            setattr(self, entity_name, _EditEntityEndpoint(edits, endpoint))


_FUNCTION_BASIC_TYPES = (str, int, float, bool, date, datetime)


def _function_param_kind(annotation: Any) -> str | None:
    """把参数标注归类为 object/basic/dict；不合法返回 None。"""

    if annotation in _FUNCTION_BASIC_TYPES:
        return "basic"
    if annotation is dict or get_origin(annotation) is dict:
        return "dict"
    for definition in OBJECT_DEFINITIONS.values():
        if annotation is definition.model_type:
            return "object"
    return None


_function_default_client: _HttpClient | None = None


def _function_client() -> _HttpClient:
    """惰性创建 function 修饰器加载实体使用的默认客户端。"""

    global _function_default_client
    if _function_default_client is None:
        _function_default_client = WorkspaceClient()._http
    return _function_default_client


def function(
    *, edits: Sequence[type[Any]]
) -> Callable[[Callable[..., list[OntologyEdit]]], Callable[..., list[dict[str, Any]]]]:
    """声明函数的下游编辑类型，符合 Palantir Python Ontology edits 写法。

    被修饰函数按 Palantir 写法构造并返回 ``list[OntologyEdit]``；
    修饰后的函数由 SDK 负责序列化，返回可直接 ``json.dumps`` 的
    编辑字典列表，调用方不需要感知 ``OntologyEdit``。
    """

    def decorate(
        func: Callable[..., list[OntologyEdit]],
    ) -> Callable[..., list[dict[str, Any]]]:
        wrapped = _decorate_function(func)
        setattr(wrapped, "__ontology_edits__", tuple(edits))
        return cast("Callable[..., list[dict[str, Any]]]", wrapped)

    return decorate


def _decorate_function(
    func: Callable[..., list[OntologyEdit]],
) -> Callable[..., list[dict[str, Any]]]:
    """把实体参数改写为按主键加载，并序列化 OntologyEdit 返回值。

    Python 不写类型标注就无法推导，因此参数和返回值都必须显式标注：
    参数类型只能是生成的实体类型、基础数据类型（str/int/float/bool/date/datetime）
    或 dict；返回值类型必须是 ``list[OntologyEdit]``。

    标注为实体类型的参数，包装后接受该实体的主键 id；调用时由 SDK 先从
    DataService 加载对象，再把加载好的实体传给原函数。对象不存在（40402）时
    记录日志并返回空 edits，不调用原函数；其它 DataService 错误继续抛出。
    已经传入实体实例的参数会原样透传。基础类型和 dict 参数不做转换。

    原函数的返回值先校验为 ``list[OntologyEdit]``，再由 wrapper 统一转换
    成可 ``json.dumps`` 的字典列表；这相当于 Palantir 平台 Function Runtime
    做的 edits 序列化，调用方拿到结果即可直接提交。
    """

    signature = inspect.signature(func)
    hints = get_type_hints(func)
    entity_params: dict[str, _ObjectDefinition] = {}
    for param in signature.parameters.values():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            raise TypeError(
                f"@function: {func.__name__!r} must not use *args or **kwargs; "
                "list each parameter with a type annotation"
            )
        if param.annotation is inspect.Parameter.empty:
            raise TypeError(
                f"@function: parameter {param.name!r} of {func.__name__!r} "
                "requires a type annotation"
            )
        annotation = hints.get(param.name)
        kind = _function_param_kind(annotation)
        if kind is None:
            raise TypeError(
                f"@function: parameter {param.name!r} of {func.__name__!r} must be "
                "a workspace entity type, a basic type (str/int/float/bool/date/datetime), "
                f"or dict, got {annotation!r}"
            )
        if kind == "object":
            for definition in OBJECT_DEFINITIONS.values():
                if annotation is definition.model_type:
                    entity_params[param.name] = definition
                    break
    if signature.return_annotation is inspect.Signature.empty or "return" not in hints:
        raise TypeError(f"@function: {func.__name__!r} requires a return type annotation")
    return_type = hints["return"]
    if get_origin(return_type) is not list or get_args(return_type) != (OntologyEdit,):
        raise TypeError(
            f"@function: {func.__name__!r} must return list[OntologyEdit], "
            f"got {return_type!r}"
        )

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        bound = signature.bind(*args, **kwargs)
        client: _HttpClient | None = None
        for name, value in list(bound.arguments.items()):
            definition = entity_params.get(name)
            if definition is None or isinstance(value, definition.model_type):
                continue
            if value is None:
                raise TypeError(
                    f"@function: parameter {name!r} of {func.__name__!r} "
                    "expects an id or entity instance, got None"
                )
            if client is None:
                client = _function_client()
            try:
                loaded: Any = EntityEndpoint(client, definition).detail(str(value))
            except DataServiceError as error:
                if error.code != 40402:
                    raise
                client._log_json(
                    "function_skipped",
                    level=logging.WARNING,
                    function=func.__name__,
                    entity=definition.entity_name,
                    primary_key=str(value),
                    reason="DataService returned OBJECT_NOT_FOUND; function skipped successfully with no edits",
                )
                return []
            if loaded is None:
                raise DataServiceError(
                    f"@function: {definition.entity_name} {value!r} not found"
                )
            bound.arguments[name] = loaded
        result = func(*bound.args, **bound.kwargs)
        if not isinstance(result, list) or any(not isinstance(item, OntologyEdit) for item in result):
            raise TypeError(f"@function: {func.__name__!r} must return list[OntologyEdit]")
        return [item.to_dict() for item in result]

    return wrapper


class Objects(Protocol):
    """由当前工作区生成的实体入口；运行时属性按对象定义动态绑定。"""

    pass


class _ObjectsRuntime:
    """将生成的实体定义绑定成 ``client.objects.<Entity>`` 属性。"""

    def __init__(self, client: _HttpClient) -> None:
        for definition in OBJECT_DEFINITIONS.values():
            setattr(self, definition.entity_name, EntityEndpoint(client, definition))


class WorkspaceClient:
    """Workspace DataService 客户端。

    生成 SDK 时已经把当前工作区的 ``workspace_id``、DataService 地址和
    Demo token 固化在 SDK 中，调用方通常只需要执行 ``WorkspaceClient()``。
    部署到其他环境时，可以通过构造参数或 ``DATASERVICE_URL``、
    ``DATASERVICE_TOKEN``、``DATASERVICE_WORKSPACE_ID`` 环境变量覆盖默认配置。

    HTTP 请求和响应通过 ``workspace_sdk.http`` logger 以 JSON Lines 记录。
    SDK 不配置全局 handler；调用方可以自行决定是否输出、输出到控制台，
    或写入日志文件。
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        workspace_id: str | None = None,
        timeout: float = 30.0,
        logger: logging.Logger | None = None,
    ) -> None:
        configured_workspace_id = (
            workspace_id
            or os.getenv("DATASERVICE_WORKSPACE_ID")
            or DEFAULT_WORKSPACE_ID
        )
        if not configured_workspace_id:
            raise ValueError(
                "workspace_id is required; pass it to WorkspaceClient or set DATASERVICE_WORKSPACE_ID"
            )
        http = _HttpClient(
            base_url=base_url or os.getenv("DATASERVICE_URL") or DEFAULT_DATASERVICE_URL,
            token=token or os.getenv("DATASERVICE_TOKEN") or DEFAULT_TOKEN,
            workspace_id=configured_workspace_id,
            timeout=timeout,
            logger=logger,
        )
        self._http = http
        self.objects: Objects = cast(Objects, _ObjectsRuntime(http))

    def edits(self) -> OntologyEdits:
        """创建一个新的 edits 容器。"""

        return OntologyEdits(self._http)

    @property
    def base_url(self) -> str:
        return self._http.base_url

    @property
    def workspace_id(self) -> str:
        return self._http.workspace_id


# ---------------------------------------------------------------------------
# HTTP 传输（放在文件末尾，便于把 SDK 领域 API 与网络细节分开）
# ---------------------------------------------------------------------------


from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_DATASERVICE_URL = "https://aquilair.idcs.elitescloud.com/data-service"
DEFAULT_TOKEN = "runtime-token"
DEFAULT_WORKSPACE_ID = "01a13967-8fba-7000-affb-2188fb661c4d"


class DataServiceError(RuntimeError):
    """DataService 请求失败或返回了不符合协议的响应。"""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class _HttpClient:
    """DataService HTTP 传输层；成功请求也通过标准 logging 输出 JSON。"""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        workspace_id: str,
        timeout: float,
        logger: logging.Logger | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.workspace_id = workspace_id
        self.timeout = timeout
        self.logger = logger or logging.getLogger("workspace_sdk.http")

    def _log_json(self, event: str, *, level: int = logging.DEBUG, **values: Any) -> None:
        """把一条 HTTP 事件编码成 JSON，交给调用方配置的 logger。"""

        record = {"event": event, **values}
        self.logger.log(
            level,
            json.dumps(record, ensure_ascii=False, default=str),
        )

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        operation: str = "",
    ) -> dict[str, Any]:
        """发送 JSON 请求，并返回 JSON object。"""

        request_url = f"{self.base_url}{path}"
        request_body = {} if body is None else dict(body)
        self._log_json(
            "http_request",
            operation=operation,
            method=method,
            url=request_url,
            body=request_body,
        )
        payload = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
        request = Request(
            request_url,
            data=payload if method != "GET" else None,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                response_body = json.loads(raw) if raw else {}
                self._log_json(
                    "http_response",
                    operation=operation,
                    status_code=response.status,
                    url=request_url,
                    body=response_body,
                )
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                error_body: Any = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                error_body = {"raw": raw}
            self._log_json(
                "http_response",
                level=logging.ERROR,
                operation=operation,
                status_code=error.code,
                url=request_url,
                body=error_body,
            )
            raw_business_code = (
                error_body.get("code") if isinstance(error_body, dict) else None
            )
            try:
                business_code = int(raw_business_code)
            except (TypeError, ValueError):
                business_code = None
            raise DataServiceError(
                f"DataService returned HTTP {error.code}: {error_body}",
                code=business_code,
                http_status=error.code,
            ) from error
        except URLError as error:
            self._log_json(
                "http_error",
                level=logging.ERROR,
                operation=operation,
                method=method,
                url=request_url,
                error=str(error.reason),
            )
            raise DataServiceError(f"DataService request failed: {error.reason}") from error

        if not isinstance(response_body, dict):
            raise DataServiceError("DataService response must be a JSON object")
        if "code" not in response_body or "message" not in response_body:
            raise DataServiceError(
                "DataService response must contain code and message"
            )
        if "data" not in response_body:
            raise DataServiceError(
                "DataService response must contain data"
            )
        data = response_body["data"]
        if not isinstance(data, dict):
            raise DataServiceError("DataService response data must be a JSON object")
        return data


__all__ = [
    "DataServiceError",
    "Page",
    "FieldRef",
    "SortField",
    "EditableObject",
    "OntologyEdit",
    "OntologyEdits",
    "EntityEndpoint",
    "ObjectSet",
    "Objects",
    "RelationDefinition",
    "RELATION_DEFINITIONS",
    "WhereExpression",
    "and_",
    "or_",
    "not_",
    "function",
    "WorkspaceClient",
]
