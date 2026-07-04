import json
import traceback
from enum import Enum
from typing import List, Dict, Any

from uitls.utils import get_dict_val


class ProjectItemType(Enum):
    Contract = 1  # 黄钻
    Order = 2  # 绿钻
    Invoice = 3


class OutputFilter:
    def __init__(self):
        pass

    def accept(self, name: str) -> bool:
        return False


class SnapshotModel:
    def __init__(self, item_type: ProjectItemType, name: str, snapshots: List[str]):
        self.item_type = item_type
        self.name = name
        self.snapshots = snapshots

    def __str__(self):
        return f'SnapshotModel {self.item_type}-{self.name}-{len(self.snapshots)}'

    def get_pre_snapshot_url(self, index: int) -> str | None:
        return self.get_snapshot_url(index - 1)

    def get_next_snapshot_url(self, index: int) -> str | None:
        return self.get_snapshot_url(index + 1)

    def get_snapshot_url(self, index: int) -> str | None:
        if index < 0 or index >= len(self.snapshots):
            return None
        else:
            return self.snapshots[index]

    def get_snapshot_count(self) -> int:
        return len(self.snapshots)

    def get_last_pos(self):
        return self.get_snapshot_count() - 1

    def to_json(self, filter1: OutputFilter | None = None) -> Dict[str, Any] | None:

        if self.snapshots is None:
            return None

        items = []
        if filter1 is not None:
            for one in self.snapshots:
                if filter1.accept(one):
                    items.append(one)
        else:
            items = self.snapshots

        if len(items) > 0:
            output = {"snapshots": items, "name": self.name}
            return output
        else:
            return None


class ProjectItemModel:
    def __init__(self, model_type: ProjectItemType, snapshots: List[SnapshotModel] | None):
        self.model_type = model_type
        self.snapshots = snapshots

    def __str__(self):
        return f'ProjectItemModel {self.model_type}-snapshots-{len(self.snapshots)}'

    def get_model_names(self) -> List[str]:
        if self.snapshots is not None:
            return [item.name for item in self.snapshots]
        else:
            return []

    def get_all_snapshots(self, output: List[SnapshotModel]) -> List[SnapshotModel]:
        if self.snapshots is not None:
            for one in self.snapshots:
                output.append(one)
            return output
        else:
            return output

    def to_json(self, wrapper_list: bool , filter1: OutputFilter | None = None) -> List[Dict[str, Any]] | None:

        items = []
        if self.snapshots is None:
            return None

        if filter1 is not None:
            for one in self.snapshots:
                out = one.to_json(filter1)
                if out is not None:
                    if wrapper_list:
                        items.append([out])
                    else:
                        items.append(out)

        else:
            for one in self.snapshots:
                out = one.to_json(None)
                if out is not None:
                    if wrapper_list:
                        items.append([out])
                    else:
                        items.append(out)

        if len(items) > 0:
            return items
        else:
            return None


class ProjectModelCursor:
    def __init__(self):
        self.sel_type = ProjectItemType.Contract
        self.sel_pos = 0


class ProjectModel:
    def __init__(self, project_id: str, meta: Dict[str, Any], contract: ProjectItemModel, orders: ProjectItemModel,
                 invoices: ProjectItemModel):
        self.project_id = project_id
        self.meta = meta
        self.contract = contract
        self.orders = orders
        self.invoices = invoices
        self.all_snapshots: List[SnapshotModel] = []
        self.init_all_snapshots()

    def __str__(self):
        return f'{self.project_id}-{self.get_project_name()}'

    def get_project_name(self) -> str:
        return self.meta['项目名称']

    def init_all_snapshots(self):
        try:
            if len(self.all_snapshots) == 0:
                self.contract.get_all_snapshots(self.all_snapshots)
                self.orders.get_all_snapshots(self.all_snapshots)
                self.invoices.get_all_snapshots(self.all_snapshots)
        except Exception as e:
            print(f"local json error {e}")
            traceback.print_stack()

    def get_snapshot_by_index(self, index: int):
        if index < 0 or index >= len(self.all_snapshots):
            return None

        return self.all_snapshots[index]

    def get_snapshot_count(self):
        return len(self.all_snapshots)

    def get_item_names(self) -> List[str]:
        item_list = []
        # 合同
        idx = 0
        for one in self.all_snapshots:
            name = one.name
            if one.item_type == ProjectItemType.Contract:
                item_list.append(f"合同-{idx}: {name}")
            elif one.item_type == ProjectItemType.Order:
                item_list.append(f"订单-{idx}: {name}")
            elif one.item_type == ProjectItemType.Invoice:
                item_list.append(f"发票-{idx}: {name}")
            else:
                assert False, f"Unknow type :{one.item_type}"

        return item_list

    def to_json(self, filter1: OutputFilter | None = None) -> Dict[str, Any] | None:
        output = {}
        output["contractId"] = self.project_id
        output["meta"] = self.meta
        has_value = False
        if self.contract:
            contract = self.contract.to_json(False,filter1)
            if contract is not None:
                output["contracts"] = contract
                has_value = True

        if self.orders:
            orders = self.orders.to_json(True, filter1)
            if orders is not None:
                output["orders"] = orders
                has_value = True

        if self.invoices:
            invoices = self.invoices.to_json(True, filter1)
            if invoices is not None:
                output["invoices"] = invoices
                has_value = True
        if has_value:
            return output
        else:
            return None


def load_snapshot(item_type: ProjectItemType, json_obj: Dict[str, Any]) -> SnapshotModel:
    if json_obj is None:
        print(f"here  , ========== {item_type} , {json_obj}")

    name = get_dict_val(json_obj, "name")
    snapshots = get_dict_val(json_obj, "snapshots")
    return SnapshotModel(item_type, name, snapshots)


def load_snapshots(item_type: ProjectItemType, json_obj_list: List[Any]) -> List[SnapshotModel]:
    output = []
    for json_obj in json_obj_list:
        one = load_snapshot(item_type, json_obj)
        output.append(one)
    return output


def load_snapshots_list(item_type: ProjectItemType, json_obj_list: List[Any]) -> List[SnapshotModel]:
    output = []
    for json_obj in json_obj_list:
        one = load_snapshots(item_type, json_obj)
        if one is not None:
            for snapshot in one:
                output.append(snapshot)
    return output


def snapshots_list_to_json(models: List[SnapshotModel], filter1: OutputFilter | None = None) -> List[Any] | None:
    output = []
    for one in models:
        if one:
            out = one.to_json(filter1)
            if out is not None:
                output.append(out)

    if len(output) > 0:
        return output
    return None


def load_project_models_from_json(json_obj: Dict[str, Any]) -> List[ProjectModel]:
    projects = get_dict_val(json_obj, "projects")
    if not projects:
        return []

    output = []
    for project in projects:
        project_model = load_project_model(project)
        output.append(project_model)
    return output


def load_project_model(json_obj: Dict[str, Any]) -> ProjectModel:
    contractId = get_dict_val(json_obj, "contractId")
    meta = get_dict_val(json_obj, "meta")
    contracts = get_dict_val(json_obj, "contracts")
    if contracts is not None and len(contracts) > 0:
        contracts_model = load_snapshots(ProjectItemType.Contract, contracts)
    else:
        contracts_model = None

    orders = get_dict_val(json_obj, "orders")
    if orders is not None and len(orders) > 0:
        orders_model = load_snapshots_list(ProjectItemType.Order, orders)
    else:
        orders_model = None

    invoices = get_dict_val(json_obj, "invoices")
    if invoices is not None and len(invoices) > 0:
        invoices_model = load_snapshots_list(ProjectItemType.Invoice, invoices)
    else:
        invoices_model = None

    contract_item = ProjectItemModel(ProjectItemType.Contract, contracts_model)
    orders_item = ProjectItemModel(ProjectItemType.Order, orders_model)
    invoices_item = ProjectItemModel(ProjectItemType.Invoice, invoices_model)
    return ProjectModel(contractId, meta, contract_item, orders_item, invoices_item)


class ProjectModelManager:
    def __init__(self):
        self.projects: List[ProjectModel] = []

    def load_from_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.load_from_dict(raw)

    def load_from_dict(self, raw: Dict[str, Any]):

        try:

            all_projects = load_project_models_from_json(raw)  # raw["projects"]
            self.projects = all_projects
        except Exception as e:
            print(f"error loading projects from json: {e}")
            traceback.print_exc()

    def get_all_project_names(self):
        names = [p.get_project_name() for p in self.projects]
        return names

    def get_project_count(self) -> int:
        return len(self.projects)

    def is_empty(self) -> bool:
        return self.projects is None or len(self.projects) == 0

    def get_project(self, idx: int) -> None | ProjectModel:
        if idx < 0 or idx >= len(self.projects):
            return None
        return self.projects[idx]

    def to_json(self, filter1: OutputFilter | None = None) -> Dict[str, Any]:

        items = []
        for one in self.projects:
            out = one.to_json(filter1)
            if out is not None:
                items.append(out)

        output = {"projects": items}
        return output
