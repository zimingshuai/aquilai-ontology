# 本体差异拓扑：supplier-recon（0.2.0-draft.1）

> 由 render_topology.py --diff 自动生成：target 相对 base（supplier-recon 0.1.0-draft.1）的差异，与 changeset.json 同一判定来源。
> 图例：绿 class=新增实体，红 class=删除，黄 class=有修改；成员行尾【新增】/【删除】/【修改】为属性级标记，
> 关联线标签尾【新增】/【删除】/【修改】为 links 级标记（持有方实体同步黄色高亮）。
> 取舍：Mermaid class 成员不支持删除线、classDiagram 的 linkStyle 渲染不生效（mermaid@11 实测），
> 删除项以红色 classDef 替代、links 变更以标签文字标记。

```mermaid
    classDiagram
    class Supplier {
        +supplier_code : STRING 🔑
        +supplier_name : STRING【修改】
        +settlement_type : STRING
        +frozen_flag : BOOLEAN
        +create_time : TIMESTAMP
        +update_time : TIMESTAMP
        +total_delivery_amount : DOUBLE【修改】
    }
    class Supplier:::diffModified
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
    class PaymentRecord {
        +payment_nr : STRING 🔑
        +payment_amount : DECIMAL
    }
    class PaymentRecord:::diffAdded
    note for ReconciliationStatement "【衍生】对账差异金额: recon_diff_amount: invoice_amount - COALESCE(reconciled_amount, 0)<br/>【衍生】对账差异率: recon_diff_rate: COALESCE(recon_diff_amount / invoice_amount, 9999)<br/>【触发】对账差异复核触发: recon_diff_amount ＞ 2000 且 recon_diff_rate ＞ 0.05<br/>【触发】【新增】大额对账单提醒: invoice_amount ＞ 100000"
    note for Supplier "【衍生】供应商交货总额: total_delivery_amount: SUM(purchase_contracts.delivery_records.delivery_amount)<br/>【触发】【删除】供应商冻结提醒: frozen_flag == true"
    Supplier "1" --> "*" PurchaseContract : supplier
    PurchaseContract "1" --> "*" DeliveryRecord : purchase_contract
    Supplier "1" --> "*" ReconciliationStatement : supplier
    classDef diffAdded fill:#e6ffe6,stroke:#2e7d32,stroke-width:2px
    classDef diffRemoved fill:#ffe6e6,stroke:#c62828,stroke-width:2px
    classDef diffModified fill:#fffbe6,stroke:#f9a825,stroke-width:2px
```

**变更摘要**：实体 新增 1 / 删除 0 / 修改 1；规则变更 2 条。

