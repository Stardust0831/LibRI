# OpenMP collapse：完整日志、成功与失败对照

GCC 13.3 下，原始 `fe27bb1` 的两个 LibRI 测试目标均编译失败。只将五处折叠循环之间的变量声明移到最内层后，两个目标均完成编译和链接。

按以下顺序阅读，完整日志放在节选之前：

1. **[最初测试的完整原始记录](01-original-libri/README.md)**：保留当时的配置、编译、测试输出及生成的编译规则，日志未删减。
2. **[实际 LibRI 源码的完整编译对照](02-libri-comparison/README.md)**：父提交、原始失败版本、移动声明后的成功版本；包含全量 verbose 输出、命令、退出码、完整源码归档和补丁。
3. **[独立的成功、失败示例](03-minimal/README.md)**：每个例子各有源码、完整编译输出、命令和退出码；能编译的例子还保留运行输出。
4. **[便于讨论的节选](04-excerpts.md)**：从完整记录中摘出错误位置和成功结果。

直接查看实际 LibRI 的关键完整日志：

| 版本 | Hartree | LR |
| --- | --- | --- |
| 最初保留的原始失败日志 | [完整日志](01-original-libri/logs/source_hartree-build.log) | [完整日志](01-original-libri/logs/source_lr-build.log) |
| 新的干净构建：原始 `fe27bb1` | [完整编译输出](02-libri-comparison/logs/before/hartree/output.log) | [完整编译输出](02-libri-comparison/logs/before/lr/output.log) |
| 新的干净构建：声明移入最内层 | [完整编译、链接输出](02-libri-comparison/logs/after/hartree/output.log) | [完整编译、链接输出](02-libri-comparison/logs/after/lr/output.log) |

也可以一次查看新对照的 **[全部命令、完整输出和退出码](02-libri-comparison/logs/full-transcript.log)**。

原先的 `Matches expectation: true` 表示失败例子确实复现了错误，并不表示编译成功。现在每个例子直接记录实际的 `FAILED` 或 `SUCCEEDED`，以及编译器退出码。

本资料验证编译问题。`after` 补丁刻意只移动声明，保留原来的取值表达式和循环上限；此前指出的两处 `list_I/list_J` 问题仍需独立处理。两个目标编译通过，不等于所有 LibRI 功能或数值计算均已验证。
