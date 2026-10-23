# 完整记录之后的节选

以下只用于快速讨论。原始输出完整保存在 [最初的编译记录](01-original-libri/README.md) 和 [实际源码对照](02-libri-comparison/README.md)，节选不替代原始日志。

## 实际 LibRI 的失败

来自 [原始版本 Hartree 的完整 verbose 日志](02-libri-comparison/logs/before/hartree/output.log)。下方只省略文件路径的目录前缀：

```text
LRI_k-cal_cvc_mo.hpp:136:17: error: not enough for loops to collapse
  136 |                 const int ik = k_indices[ik_index];
      |                 ^~~~~
```

同类错误出现于 `LRI_k-cal_cvc_mo.hpp:136,310,468` 和 `LRI_k-cal_hartree.hpp:124,208`。两个测试目标的构建命令均返回 `2`。

## 实际 LibRI 的成功

来源为 [移动声明后 Hartree 的完整日志](02-libri-comparison/logs/after/hartree/output.log) 和 [LR 的完整日志](02-libri-comparison/logs/after/lr/output.log)，退出码来自各自的 `exit-code.txt`：

```text
[100%] Linking CXX executable after_hartree
[100%] Built target after_hartree
Build command exit code: 0
[100%] Linking CXX executable after_lr
[100%] Built target after_lr
Build command exit code: 0
```

改动只有 [五处折叠循环内声明位置的移动](02-libri-comparison/move-declarations.patch)。完整头文件与完整源码归档均附在实际源码对照文件夹中。

## 独立示例的差异

失败例子的两层循环之间有声明：

```cpp
#pragma omp parallel for collapse(2)
for (int i = 0; i < k_indices.size(); ++i) {
    const int ik = k_indices[i];
    for (int j = 0; j < atoms.size(); ++j) {
        const int atom = atoms[j];
        // 计算
    }
}
```

成功例子保留下标循环，把声明放到最内层：

```cpp
#pragma omp parallel for collapse(2)
for (int i = 0; i < k_indices.size(); ++i) {
    for (int j = 0; j < atoms.size(); ++j) {
        const int ik = k_indices[i];
        const int atom = atoms[j];
        // 计算
    }
}
```

这些代码块是结构节选；可直接编译的完整程序和未经截取的日志见 [独立示例](03-minimal/README.md)。
