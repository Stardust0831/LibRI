# PR #8169 最终版本：移除旧补丁后的完整验证

**ABACUS 完整 GPU 构建、CPU/GPU 输入测试和八组 HSE 计算全部通过。** 本记录对应 [PR #8169](https://github.com/deepmodeling/abacus-develop/pull/8169) 的最终提交 [`b30b66a5a`](https://github.com/deepmodeling/abacus-develop/commit/b30b66a5a333a2667d618932f8430a80dd92146a)：已移除三个旧 LibRI 兼容补丁，并合入 `develop` 的 `370ba685e`。

依赖为 LibRI `fac_add_Ds` 的 `f68342122e4d23007142028bf2d017ce026835eb`、DDLA v0.0.4（`9c404ac65148ec1b48977b846f38ba6ef9e134f7`）。LibRI 仍需独立的 [OpenMP 声明移动补丁](move-declarations.patch)：将两个头文件中五处折叠循环之间的六条声明移入最内层；原来的三个兼容补丁均未应用。工具链为 GCC 13.3/OpenMP、CUDA 和 NVIDIA V100，运行使用 `OMP_NUM_THREADS=1`。

完整原始日志如下，未经删减或路径替换：

| 验证 | 完整日志 |
| --- | --- |
| ABACUS 配置 | [配置输出](results/abacus/configure/output.log) |
| BSE 目标编译 | [verbose 编译输出](results/abacus/bse-build/output.log) |
| 完整 `abacus_std_gpu` 编译、链接 | [verbose 编译及链接输出](results/abacus/full-build/output.log) |
| CPU LibRI 消费端 | [配置](results/consumer-cpu/configure/output.log)、[编译](results/consumer-cpu/build/output.log)、[测试](results/consumer-cpu/test/output.log) |
| GPU LibRI 消费端和数值测试 | [配置](results/consumer-gpu/configure/output.log)、[编译](results/consumer-gpu/build/output.log)、[测试](results/consumer-gpu/test/output.log) |
| GPU/CPU 配置下的输入测试 | [GPU 测试](results/input-gpu/test/output.log)、[CPU 测试](results/input-cpu/test/output.log) |
| CLI 检查 | [CLI 结果](results/abacus/cli/output.log) |
| HSE Γ 点，1 MPI 进程 | [完整自动测试日志](results/scf_hse_gamma/autotest.log)、[原始输入和计算输出](results/scf_hse_gamma/tests/08_RI/) |
| HSE 复数多 k 点，2 MPI 进程 | [完整自动测试日志](results/scf_hse_complex_multik_mpi2/autotest.log)、[原始输入和计算输出](results/scf_hse_complex_multik_mpi2/tests/08_RI/) |
| 所有阶段的命令和退出码 | [summary.json](results/summary.json) |
| 作业最终状态 | [调度记录](results/scheduler.txt) |

结果摘要：

- 完整程序编译、链接成功，包括此前报错的 BSE 目标。
- CPU 依赖测试 1/1、GPU 依赖测试 2/2 通过；实数和复数各 18 类带符号系数的张量收缩全部通过。
- 启用和关闭 GPU RI 时，输入单测各 16/16 通过，包括 `device_exx` 和合并时保留的两项 `mem_saver` 测试。
- 八组 HSE 计算全部通过未修改的仓库参考值。每个算例各运行 CPU 求解器/CPU RI、GPU 求解器/默认 RI、GPU 求解器/显式 CPU RI、GPU 求解器/GPU RI 四种组合。Γ 点检查能量、力和应力；复数多 k 点检查能量，GPU RI 使用两张 GPU。
- 16 组额外数值比较全部通过，覆盖 CPU/GPU 对照及此前“LibRI `6ce3c84` 加三个兼容补丁”的历史结果。与历史结果相比，最大能量差为 **1.28×10⁻¹⁰ eV**，最大力分量差为 **3.00×10⁻¹⁰ eV/Å**，应力在打印精度内一致。见 [完整比较数据](results/component-comparison.json) 和 [验证摘要](results/validation-summary.json)。

[previous-results](previous-results/) 保留用于比较的历史输出。重新执行数值比较：

```sh
python3 control/compare_results.py --results results --previous previous-results
```

测试先于提交完成，原始 [manifest.json](manifest.json) 因此将 `source_sha` 记录为 `null`，同时保存了实际测试的 Git tree `17f2f18ce697201513fc18fbdc626cb9083ea331` 及两个父提交。[committed-source.json](committed-source.json) 记录随后创建的 `b30b66a5a`，其 tree 与测试源码完全相同。

[control](control/) 保存构建及测试脚本，[build-records](build-records/) 保存 CMake 配置和编译数据库。[原始 LibRI](libri.tar.gz) 与 [补丁后的 LibRI](libri-fixed.tar.gz) 均完整保留；[SHA256SUMS.json](SHA256SUMS.json) 记录全部原始资料的哈希。SAI 作业 `1912596` 最终状态为 `COMPLETED / 0:0`。

本轮验证覆盖 HSE/DDLA。BSE 已编译，但未验证其数值路径；此前发现的两处 `list_I/list_J` 问题仍在 LibRI，未纳入声明移动补丁。旧 Si64 性能基准未重跑。
