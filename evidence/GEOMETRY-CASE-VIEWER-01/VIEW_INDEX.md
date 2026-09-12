# GEOMETRY-CASE-VIEWER-01

正常入口：运行仓库根目录 `start_geometry_viewer.ps1`，打开打印的本机 URL，选择一个 `.dmslicer` 文件。

| 样包 | 输入 / 公共补丁 / 其他 |
| --- | --- |
| `case01-package-002/CASE01.dmslicer` | A/G/B 三输入；A-G/G-B 两公共补丁；融合：本证据未产生 |
| `c02-package-004/C02.dmslicer` | 两原始输入、两校正对象、一公共补丁、一融合结果 |
| `u05-package-004/U05.dmslicer` | 两输入、一公共补丁、一剩余分区、一融合结果 |
| `final-inspection-003/C02-portable-core.dmslicer` | 无缓存、无 FCStd、无 BREP；可阅读已有计算结果，当前平台不生成网格 |

`final-inspection-003/CASE01.html`、`C02.html`、`U05.html` 是最终离线预览。早期 package 目录内 preview.html 可能包含已废止的入口文案，不作为当前产品验收入口，保留仅用于变更追溯。

19 项代码测试结果见 `catalog-001/labeled-tests.junit.xml`；三真实包及核心包实际 HTTP 导入见 `final-inspection-003/checks.json`。这些是导入/显示数据检查，不是几何实验重新 PASS。

人工视觉状态见 `HUMAN_REVIEW.md`。所有 `.dmslicer`、HTML、JUnit 和采样详细输出当前仅保留在本地稳定 evidence 路径，被显式 Git ignore。未上传、未确认第二份可恢复的独立备份，因此不能称为研究证据已完全保存，也不能据此删除旧工作树。
