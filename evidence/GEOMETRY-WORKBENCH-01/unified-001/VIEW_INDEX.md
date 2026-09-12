# 统一工作台检查入口

- 运行仓库根目录 `start_geometry_viewer.ps1` 或打开 `http://127.0.0.1:56810/`。
- 手动导入一个 `.dmslicer` 文件，或使用同页的示例选择器。
- `browser-live/checks.json`：实际固定端口的五类样包自动浏览器验证。
- `browser-live/*-comparison.png`：各案例分栏截图；`pmulti-narrow.png`：窄屏六栏。
- `final-tests.junit.xml`：22 项针对性测试。
- `red.junit.xml`：功能实现前的两项失败测试，保留。
- `services-before.json` / `services-after.json`：经核对命令行后完成的服务切换。
- `samples.json`：明确的样包 allowlist、来源和字节完整性记录。

大样包、截图与 JUnit 留在本地稳定 evidence 路径，未远程发布。源文件及复制后的样包都存在且字节校验相符，但未建立独立灾备，不能据此建议删除历史工作树。
