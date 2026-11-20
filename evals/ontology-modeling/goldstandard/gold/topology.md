# 本体拓扑：supplier-recon（0.1.0-draft.1）

> 由 render_topology.py 从 DSL 自动生成；仅含实体 + links + 规则三要素，不含能力问题（CQ）。
> 图例：🔑 = 主键；关联线 `目标 "1" --> "*" 持有方 : 别名` = 持有方实体的 links 别名持有指向目标的引用；
> 【衍生】= derived_property（目标字段: 表达式）；【触发】= trigger 条件摘要（多条件合取）。

```mermaid
    classDiagram
    class Supplier {
        +supplier_code : STRING 🔑
        +supplier_name : STRING
        +settlement_type : STRING
        +frozen_flag : BOOLEAN
        +create_time : TIMESTAMP
        +update_time : TIMESTAMP
        +total_delivery_amount : DECIMAL
    }
    class PurchaseContract {
        +contract_nr : STRING 🔑
        +contract_amount : DECIMAL
        +sign_date : DATE
        +status : STRING
        +supplier_code : STRING
    }
    class DeliveryRecord {
        +delivery_nr : STRING 🔑
        +delivery_qty : DOUBLE
        +delivery_amount : DECIMAL
        +delivery_date : DATE
        +contract_nr : STRING
    }
    class ReconciliationStatement {
        +recon_nr : STRING 🔑
        +recon_period : STRING
        +invoice_amount : DECIMAL
        +reconciled_amount : DECIMAL
        +status : STRING
        +create_time : TIMESTAMP
        +supplier_code : STRING
        +recon_diff_amount : DECIMAL
        +recon_diff_rate : DECIMAL
    }
    note for ReconciliationStatement "【衍生】recon_diff_amount: invoice_amount - COALESCE(reconciled_amount, 0)<br/>【衍生】recon_diff_rate: COALESCE(recon_diff_amount / invoice_amount, 9999)<br/>【触发】对账差异复核触发: recon_diff_amount ＞ 2000 且 recon_diff_rate ＞ 0.05"
    note for Supplier "【衍生】total_delivery_amount: SUM(purchase_contracts.delivery_records.delivery_amount)<br/>【触发】供应商冻结提醒: frozen_flag == true"
    Supplier "1" --> "*" PurchaseContract : supplier
    PurchaseContract "1" --> "*" DeliveryRecord : purchase_contract
    Supplier "1" --> "*" ReconciliationStatement : supplier
```
