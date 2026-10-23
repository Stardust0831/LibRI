# 实际 LibRI 源码：完整编译对照

本次从干净目录编译 LibRI 现有的 `Hartree-test.hpp` 和 `LR-test.hpp`。两个入口文件只调用原有测试，不替换其实现。所有构建均使用相同的 GCC 13.3、OpenMP、OpenMPI 和 OpenBLAS 配置。

**[全部命令、完整输出和退出码](logs/full-transcript.log)** 包含配置步骤及六个目标的完整 verbose 构建记录。下面按成功、失败分别链接原始输出：

| 源码 | Hartree | LR | 构建退出码 |
| --- | --- | --- | ---: |
| `parent`：父提交 `d891fd9` | [编译、链接成功](logs/parent/hartree/output.log) | [编译、链接成功](logs/parent/lr/output.log) | 0 |
| `before`：原始 `fe27bb1` | [编译失败](logs/before/hartree/output.log) | [编译失败](logs/before/lr/output.log) | 2 |
| `after`：`fe27bb1` 上仅移动声明 | [编译、链接成功](logs/after/hartree/output.log) | [编译、链接成功](logs/after/lr/output.log) | 0 |

每个日志目录另有 `command.txt` 和 `exit-code.txt`。`output.log` 是 stdout/stderr 合并后的完整原始输出；未做路径替换或删除。这里的失败退出码 `2` 来自 CMake/Make 构建命令；独立示例中的 `1` 来自直接调用 GCC，两者都表示编译失败。

[results.json](logs/results.json) 记录实际结果，以及成功生成的四个可执行文件的大小和 SHA-256。[compile_commands.json](logs/compile_commands.json) 保存六个目标的完整编译命令。

`after` 只移动五处折叠循环中的六条声明，改动见 **[完整补丁](move-declarations.patch)**。两个头文件修改前后的完整内容见 [snapshots](snapshots/)，三个版本的完整 LibRI 源码见 [source-archives](source-archives/)。归档哈希和固定版本见 [provenance.json](provenance.json)。

为单独验证编译原因，补丁保留了原来的 `list_I/list_J` 表达式和循环上限。此前发现的两处列表错误没有混入这份补丁；因此这里不声称 `after` 已修复全部逻辑问题。

复现需要 GCC、CMake、MPI、OpenMP、OpenBLAS，以及 LibComm 和 cereal 的头文件。使用一个新的输出目录保存本次复现结果：

```sh
python3 run.py \
  --libcomm-root /path/to/LibComm \
  --cereal-root /path/to/cereal \
  --blas-library /path/to/libopenblas.so \
  --output-dir /path/to/new-comparison
```

原始执行脚本和模块环境也完整保存在 [recorded-environment](recorded-environment/)。复现脚本的总体退出码用于确认对照已按预期完成；每个构建是否成功，以各自的退出码和上述表格为准。

这里只运行编译和链接，未执行修改后版本的 Hartree/LR 数值测试，也未重新构建或运行完整 ABACUS。
