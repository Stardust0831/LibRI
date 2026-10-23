# LibRI 编译与 ABACUS GPU 验证记录

完整资料在 **[openmp-collapse 文件夹](openmp-collapse/README.md)**。

先提供实际 LibRI 的完整原始编译日志，再提供修改前后的实际源码编译对照，最后是独立示例和节选。

| 实际 LibRI 源码 | Hartree 测试目标 | LR 测试目标 |
| --- | --- | --- |
| 父提交 `d891fd9` | 编译、链接成功 | 编译、链接成功 |
| 原始 `fe27bb1` | 编译失败 | 编译失败 |
| `fe27bb1`，仅把声明移入最内层循环 | 编译、链接成功 | 编译、链接成功 |

工具链为 GCC 13.3、OpenMP、OpenMPI 和 OpenBLAS。这是两个实际测试目标的编译验证；本次对修改后的版本没有执行物理数值测试。

另有 **[ABACUS 接入未打补丁 LibRI 的实测记录](abacus-unpatched/README.md)**：最新 `fac_add_Ds` 的依赖测试通过，但实际 ABACUS BSE 目标被同一 OpenMP 编译问题阻塞，尚未运行 HSE 算例。

后续 **[加入移动声明补丁的完整 ABACUS 验证](abacus-collapse-fixed/README.md)** 已通过：完整编译、链接成功，八组 HSE 计算均通过参考值检查；能量、力、应力也与 CPU 及先前版本的结果一致。

最新 **[PR #8169 最终提交的完整验证](abacus-merged/README.md)** 对应 `b30b66a5a`：已移除三个旧兼容补丁并合入 `develop`，完整 GPU 构建、CPU/GPU 各 16 项输入测试和八组 HSE 计算均通过。该目录保留最终版本的完整原始日志及数值对照。

另见 **[GPU 实空间对称性缺陷与修复验证](gpu-symmetry/README.md)**：包含原始版本、维护者修复及补充修复的逐项数值对照，完整原始编译日志，以及 ABACUS 对称性计算结果。
