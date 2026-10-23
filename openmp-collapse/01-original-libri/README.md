# 最初测试的完整原始记录

这里收录最初验证开发者 `fac_add_Ds` 分支时保留的原始输出。文件按原字节复制，未截断、未过滤报错，也保留了原路径。

| 记录 | 完整文件 |
| --- | --- |
| 原始 `fe27bb1` 的 Hartree 编译失败 | [source_hartree-build.log](logs/source_hartree-build.log) |
| 原始 `fe27bb1` 的 LR 编译失败 | [source_lr-build.log](logs/source_lr-build.log) |
| 父提交 `d891fd9` 的 Hartree 编译成功 | [baseline_hartree-build.log](logs/baseline_hartree-build.log) |
| 父提交 `d891fd9` 的 LR 编译成功 | [baseline_lr-build.log](logs/baseline_lr-build.log) |
| 当时工程的配置输出 | [configure.log](logs/configure.log) |
| 当时 CPU/GPU 回归目标的构建输出 | [build.log](logs/build.log) |
| 整个验证作业的输出 | [job.log](logs/job.log) |
| 编译器与模块版本 | [compiler.txt](logs/compiler.txt)、[modules.txt](logs/modules.txt) |
| 原始编译选项、编译规则、链接命令 | [cmake-targets](cmake-targets/) |
| 当时执行的构建与验证脚本 | [control/validate.sbatch](control/validate.sbatch)、[CMakeLists.txt](control/CMakeLists.txt) |

当时没有启用 verbose 构建，所以成功目标的日志只有几行。这些文件仍是当时保留的完整输出。为便于核查实际编译命令，后续另做了 [干净的 verbose 构建对照](../02-libri-comparison/README.md)，不替换这里的历史记录。

[logs](logs/) 还包含当时全部数值测试输出，包括父提交 LR 的参考值容差断言失败；它能编译，与运行测试通过是两件事。最初外部测试工程遗漏头文件搜索目录的一次失败保留在 [initial-harness-attempt](initial-harness-attempt/)，不属于 LibRI 的 `collapse` 错误。

源码版本见 [source.json](source.json)，日志校验和见 [SHA256SUMS.json](SHA256SUMS.json)。原始 `fe27bb1` 和父提交的完整源码归档位于 [source-archives](../02-libri-comparison/source-archives/)。
