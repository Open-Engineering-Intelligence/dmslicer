# 保留的失败与设计修正

- 初始 catalog 测试 7 FAIL：模块尚未实现。`catalog-001/red.junit.xml`。
- 初始 archive 测试 6 FAIL：包读取器尚未实现。`catalog-001/package-red.junit.xml`。
- 路径测试首次 1 FAIL：Windows ZipInfo 构造器规范化反斜杠，测试未实际生成恶意名称。改为写入原始 ZIP 名，并校验 orig_filename。`catalog-001/unit.junit.xml` 保留原失败。
- U05 package-001：手写输入 fixture 路径错误，读文件失败；查询源 manifest 后改用 `benchmarks/cylinder_fit_04b/U05_cylinder_short_core/inputs.step`，在新目录 package-002 运行。
- package-002：真实 STEP 顶层是复合装配容器，原显示检查只有一个输入对象；检查记录在 `catalog-001/package-inspection.json`。修正为按本次导入的实体子对象展开，所有 ordinal 仅作 run-local diagnostic；最终包是 package-003。旧包未覆盖。
- 中途方向包含裸 STEP / 本机重建；依据最终用户范围，当前产品已删除两个入口和对应 HTTP 操作。历史测试/JUnit 和旧预览仍作为过程记录，不是最终验收物。
- CASE01 新测试先 1 FAIL（打包器未实现）：`catalog-001/case01-red.junit.xml`。实现只读取现成几何/显示 JSON，未调用 CAD。

失败发生时源码未提交，故没有独立 failure commit。导入器修正实现落在 `1853979`；CASE01 后续适配落在 `86c41b6`。本地详细输出未发布。
