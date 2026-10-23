# 移动声明后：完整 ABACUS 编译与 HSE 回归

**完整 ABACUS 编译、链接成功，八组 HSE 计算全部通过。** 测试使用 PR #8169 的 `d098ea5ef77e3b48a775795c37955b3e2d26c04c`，配合 LibRI `fac_add_Ds` 的 `f68342122e4d23007142028bf2d017ce026835eb`、DDLA v0.0.4、GCC 13.3/OpenMP 和 NVIDIA V100/CUDA。

LibRI 只增加了 [移动声明补丁](move-declarations.patch)：将两份头文件中五处折叠循环之间的六条声明移至最内层。其余 113 个头文件与原始提交完全相同。原来的三个 ABACUS 兼容补丁均未应用。

完整原始日志先列在这里；输出未经删减或路径替换：

| 验证 | 结果 | 完整日志 |
| --- | --- | --- |
| ABACUS 配置 | 成功 | [配置输出](results/abacus/configure/output.log) |
| 之前失败的 BSE 目标 | 编译成功 | [verbose 编译输出](results/abacus/bse-build/output.log) |
| 完整 `abacus_std_gpu` | 编译、链接成功 | [verbose 编译及链接输出](results/abacus/full-build/output.log) |
| CPU LibRI 消费端 | 1/1 测试通过 | [测试输出](results/consumer-cpu/test/output.log) |
| GPU LibRI 消费端及系数累加 | 2/2 测试通过；实数、复数各 18 类收缩 | [测试输出](results/consumer-gpu/test/output.log) |
| 版本、帮助、元数据和旧关键词拒绝 | 通过 | [CLI 结果](results/abacus/cli/output.log)、[版本](results/version.txt) |
| HSE Γ 点，1 MPI 进程 | 四种组合的能量、力、应力均通过仓库参考值检查 | [全部算例输出](results/scf_hse_gamma/autotest.log) |
| HSE 复数多 k 点，2 MPI 进程 | 四种组合的能量均通过仓库参考值检查 | [全部算例输出](results/scf_hse_complex_multik_mpi2/autotest.log) |

每个算例分别运行 CPU 求解器/CPU RI、GPU 求解器/默认 RI、GPU 求解器/显式 CPU RI、GPU 求解器/GPU RI，共八次 SCF。所有运行使用 `OMP_NUM_THREADS=1`；双进程 GPU RI 使用两张 GPU。Γ 点是具有非零力和应力的三原子水分子算例。复数多 k 点算例未启用力和应力计算。

参考值及其判据保持原样。另逐一比较所有力、应力分量，并与此前“LibRI `6ce3c84` 加三个兼容补丁”的历史 ABACUS 结果对照。16 组数值比较均通过，完整数据见 [component-comparison.json](results/component-comparison.json)。

| 比较 | 最大能量差 / eV | 最大力分量差 / eV·Å⁻¹ | 最大应力分量差 / kbar |
| --- | ---: | ---: | ---: |
| Γ 点，CPU RI 与 GPU RI，同用 GPU 求解器 | 4.55×10⁻¹³ | 1.00×10⁻¹⁰ | 日志打印精度内一致 |
| 复数多 k 点，CPU RI 与 GPU RI，同用 GPU 求解器 | 4.22×10⁻¹¹ | 未计算 | 未计算 |
| 八个算例分别与先前对应结果比较 | 2.71×10⁻¹¹ | 4.00×10⁻¹⁰ | 日志打印精度内一致 |

完整原始算例输入、输出与仓库参考值分别在 [Γ 点结果目录](results/scf_hse_gamma/tests/08_RI/) 和 [多 k 点结果目录](results/scf_hse_complex_multik_mpi2/tests/08_RI/)。[previous-results](previous-results/) 保存此次比较使用的历史日志。可在本目录重新执行数值比较：

```sh
python3 control/compare_results.py --results results --previous previous-results
```

[manifest.json](manifest.json) 固定源码提交、补丁和归档哈希；[原始 LibRI](libri.tar.gz) 与 [补丁后的 LibRI](libri-fixed.tar.gz) 均完整保留。[control](control/) 保存构建与测试脚本；[build-records](build-records/) 保存 CMake 配置和编译数据库；[SHA256SUMS.json](SHA256SUMS.json) 记录原始资料哈希。实际作业完成状态为 `COMPLETED / 0:0`，见 [调度记录](results/scheduler.txt)。

本次确认的是完整程序可编译，以及所测 HSE/DDLA 路径与参考结果一致。BSE 模块编译成功并不代表其所有数值路径已验证；此前记录的两处 `list_I/list_J` 混用未包含在这个只移动声明的补丁中。本次没有修改 ABACUS PR。
