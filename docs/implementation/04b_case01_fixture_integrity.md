# 04B 收口：CASE01 文件完整性校验

## 根因

`tests/test_case01.py` 在提交 `79f60fa7b845f917537c8328b1861ae1ec3f131e`
引入的固定 SHA-256 常量为
`1cd94489b4709e5292acd8df177950b9acc4c0372016eeefbf889f26170f84de`。
该值不对应仓库任一可达提交中的 `benchmarks/interface_case01/case01.step`。

权威 fixture 原始 bytes 来自首次引入该文件的提交
`7b424f5f2dce10b0b01ecc8f753cecfa7935d97f`；相同 blob 也存在于
`19354277520c40bf61193525cbf213946dbbb511` 和本轮开始的 04B HEAD。
其长度为 22,259 bytes、无 UTF-8 BOM、576 个 LF、0 个 CRLF，SHA-256 为
`089629b5d4e081bc208f49abad3329d0dade9b1de0525e97cb06d75ef43bdbae`。

## 修复与边界

仅把完整性断言改为上述可追溯 blob 的固定 SHA-256。STEP、解析几何 truth、
输入生成和几何算法均未修改。`.gitattributes` 对 `*.step` 明确设置 `-text`，
工作树、index、HEAD 和基线的原始字节完全相同，因此本次不是 checkout、编码或
本地文件异常。固定 hash 断言仍会在 fixture 的任意字节变异时失败。
