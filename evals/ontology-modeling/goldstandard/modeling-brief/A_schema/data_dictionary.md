# 供应商对账域 · 数据字典（ISO 11179 简化版）

| table | field | business_term | definition（口径） | data_type | enum | pk/fk | source |
|---|---|---|---|---|---|---|---|
| supplier | supplier_code | 供应商编码 | SRM 系统供应商唯一编码 | STRING | — | PK | SRM |
| supplier | supplier_name | 供应商名称 | 供应商营业执照全称 | STRING | — | — | SRM |
| supplier | settlement_type | 结算方式 | 与供应商约定的付款周期 | STRING | 月结30天/月结60天/货到付款 | — | SRM |
| supplier | frozen_flag | 冻结标记 | 1=冻结（合同纠纷或质检问题时冻结，停止对账与付款）；0=正常 | BOOLEAN | — | — | SRM |
| supplier | create_time | 创建时间 | 供应商主数据创建时间 | TIMESTAMP | — | — | SRM |
| supplier | update_time | 更新时间 | 供应商主数据最近更新时间 | TIMESTAMP | — | — | SRM |
| purchase_contract | contract_nr | 采购合同号 | SRM 合同唯一编号 | STRING | — | PK | SRM |
| purchase_contract | supplier_code | 签约供应商 | 合同签约方的供应商编码 | STRING | — | FK→supplier | SRM |
| purchase_contract | contract_amount | 合同总金额 | 合同含税总金额（元） | DECIMAL | — | — | SRM |
| purchase_contract | sign_date | 签约日期 | 合同签署日期 | DATE | — | — | SRM |
| purchase_contract | status | 合同状态 | 生效=正常履约；终止=到期或提前终止；作废=签署后取消 | STRING | 生效/终止/作废 | — | SRM |
| delivery_record | delivery_nr | 交货单号 | WMS 交货单唯一编号 | STRING | — | PK | WMS |
| delivery_record | contract_nr | 关联合同 | 本次交货所属采购合同 | STRING | — | FK→purchase_contract | WMS |
| delivery_record | delivery_qty | 交货数量 | 本次交货件数 | DOUBLE | — | — | WMS |
| delivery_record | delivery_amount | 交货金额 | 本次交货金额（元，含税） | DECIMAL | — | — | WMS |
| delivery_record | delivery_date | 交货日期 | 实际到货日期 | DATE | — | — | WMS |
| reconciliation_statement | recon_nr | 对账单号 | FIM 对账单唯一编号 | STRING | — | PK | FIM |
| reconciliation_statement | supplier_code | 对账供应商 | 本对账单对应的供应商 | STRING | — | FK→supplier | FIM |
| reconciliation_statement | recon_period | 对账期间 | 对账月份，格式 yyyy-MM | STRING | — | — | FIM |
| reconciliation_statement | invoice_amount | 发票金额 | 供应商本期开具发票总额（元） | DECIMAL | — | — | FIM |
| reconciliation_statement | reconciled_amount | 已对账金额 | 双方核对一致确认的金额（元） | DECIMAL | — | — | FIM |
| reconciliation_statement | status | 对账状态 | open=对账中；confirmed=双方确认；disputed=存在争议 | STRING | open/confirmed/disputed | — | FIM |
| reconciliation_statement | create_time | 创建时间 | 对账单创建时间 | TIMESTAMP | — | — | FIM |
