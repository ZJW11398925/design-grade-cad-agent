# EP-R1-IFC-001 — IFC Footprint / Body / Placement / Identity Round-trip

**状态：** `planned-mandatory-spike`  
**服务范围：** R1.6；R1-G01 / R1-G08；COV-13、COV-17、COV-19。

## Decision Question

Canonical BuildingObject 能否映射为 IFC 中可区分的 2D Footprint、3D Body 与 ObjectPlacement，并在写出、重新打开和读取后保持对象身份、placement 与几何一致性，而不把 IFC GlobalId 当 canonical primary key？

## 最小 Fixture

- 一个矩形建筑；
- 一个带凹槽或孔洞的 footprint；
- 已确认 height 与 base elevation；
- stable canonical object_id；
- 至少一次 placement 变化与一次 footprint/height revision。

## Required Artifacts

- input Canonical BuildingObject；
- IFC file before/after round-trip；
- mapping manifest：canonical object_id ↔ IFC GlobalId/representation IDs；
- Footprint representation extraction；
- Body geometry extraction/projection；
- ObjectPlacement matrix；
- round-trip diff report；
- method/library version and schema version。

## Required Checks

- same canonical object remains traceable after IFC reopen；
- Footprint 与 Body projection 在声明容差政策下保持一致；
- height/base elevation/placement 可回读；
- editing external IFC does not directly mutate canonical；
- changed external file produces `external_unreconciled` + diff/proposal；
- unsupported representation returns structured failure。

## Gate Conditions

`pass_for_scope`：上述 mapping 与 round-trip checks 可复跑，并证明 IFC adapter 是派生/互操作层，不成为第二个 design truth owner。

## 通过后仍不能宣称

- 完整 BIM authoring；
- 所有 IFC viewer/editor 一致；
- IFC4x3 全能力或道路 IFC 已解决；
- IFC 文件天然符合项目交付要求。
