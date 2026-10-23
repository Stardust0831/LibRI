# ABACUS 接入未打补丁的 fac_add_Ds

使用 ABACUS PR #8169 的 `d098ea5ef77e3b48a775795c37955b3e2d26c04c`，直接接入 Gitee `fac_add_Ds` 的 `f68342122e4d23007142028bf2d017ce026835eb` 和 DDLA v0.0.4。没有应用 ABACUS 中的三个兼容补丁，也没有对 LibRI 作其他修改。工具链为 GCC 13.3、OpenMP、CUDA 和 NVIDIA V100；运行测试使用 `OMP_NUM_THREADS=1`。

**[实际 ABACUS BSE 目标的完整 verbose 编译日志](results/abacus/bse-build/output.log)** 保留全部命令、包含路径、错误信息和 Make 退出过程。命令与退出码另存于同目录。这次在必要目标 `bse` 编译失败后停止，未构建完整可执行文件，也未运行 HSE 计算。

| 检查 | 结果 | 完整原始日志 |
| --- | --- | --- |
| CPU LibRI 消费端：配置、编译、测试 | 通过，1/1 测试 | [配置](results/consumer-cpu/configure/output.log)、[编译](results/consumer-cpu/build/output.log)、[测试](results/consumer-cpu/test/output.log) |
| GPU LibRI 消费端及带符号累加 | 通过，2/2 测试；实数、复数各 18 类收缩 | [配置](results/consumer-gpu/configure/output.log)、[编译](results/consumer-gpu/build/output.log)、[测试](results/consumer-gpu/test/output.log) |
| ABACUS GPU 配置及 LibRI/DDLA 编译链接探测 | 通过 | [配置日志](results/abacus/configure/output.log) |
| ABACUS `bse` 目标 | 编译失败，退出码 2 | [编译日志](results/abacus/bse-build/output.log) |
| 完整可执行文件及 HSE 能量、力、应力回归 | 未执行，前置目标编译失败 | — |

BSE 在启用 LCAO 和 LibRI 时参与标准构建，其 `molecular_lri.h` 包含 LibRI 的 `LR.h`，进而包含这两个 `LRI_k` 实现头文件。因此，即便计划只运行 HSE，标准构建仍会遇到这些编译错误。

日志中的五处首要诊断均为 `error: not enough for loops to collapse`：

| LibRI 文件 | 行号 |
| --- | --- |
| `LRI_k-cal_cvc_mo.hpp` | 136、310、468 |
| `LRI_k-cal_hartree.hpp` | 124、208 |

其原因与 [LibRI 编译对照](../openmp-collapse/02-libri-comparison/README.md) 相同：折叠循环之间插入了变量声明。当前记录没有将移动声明的修复混入 `f683421`，也没有关闭 OpenMP 或绕过 BSE。

三个旧补丁对应的接口名、清理接口和 GPU 系数累加修改已包含在该分支中；这轮依赖测试通过，但完整 ABACUS 接入仍被另一个编译问题阻塞。本轮没有修改 ABACUS PR，不能将上述通过项表述为完整 HSE 集成验证通过。

原始环境、逐步命令、退出码和作业状态都在 [results](results/)。[build-records](build-records/) 保留 CMakeCache 和完整的 CMake 编译数据库；数据库是配置生成的命令列表，不表示全部命令都已执行。[control](control/) 是本次实际执行的脚本；其后半段完整构建及算例步骤因前置失败而没有执行。

[manifest.json](manifest.json) 固定双方提交和源码归档哈希，[libri.tar.gz](libri.tar.gz) 保存实际使用的完整 LibRI 源码。[libri-header-sha256.json](results/libri-header-sha256.json) 记录远端实际头文件；115 个头文件已逐一确认与原始归档一致。[SHA256SUMS.json](SHA256SUMS.json) 保存本文件夹原始资料的哈希。
