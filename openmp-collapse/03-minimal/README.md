# 独立的成功、失败示例

每个文件夹都是完整的小程序，含 `main()`。失败例子把变量声明放在两层 `collapse(2)` 循环之间；成功例子只把该声明移到内层。

| 例子 | 源码 | 完整编译日志 | 实际结果 |
| --- | --- | --- | --- |
| 层间声明 | [failure/main.cpp](failure/main.cpp) | [failure/compile.log](failure/compile.log) | 编译失败，退出码 1，未运行 |
| 声明移入最内层 | [success/main.cpp](success/main.cpp) | [success/compile.log](success/compile.log) | 编译、链接成功，退出码 0；运行成功 |
| 原来的范围循环 | [range-for-reference/main.cpp](range-for-reference/main.cpp) | [range-for-reference/compile.log](range-for-reference/compile.log) | 编译、链接成功，退出码 0；运行成功 |

编译使用 `g++ -v -std=c++17 -fopenmp main.cpp -o example`。`-v` 保留 GCC 的完整编译过程、头文件搜索路径和链接过程；日志未截取。每个文件夹另有原始命令和退出码文件。

能编译的程序使用两个 OpenMP 线程，检查全部 12 个循环结果，运行输出分别见 [success/run.log](success/run.log) 和 [range-for-reference/run.log](range-for-reference/run.log)。编译器版本见 [compiler.log](compiler.log)。这些例子验证循环结构，不代表实际 LibRI 数值测试。

重新生成这些记录：

```sh
python3 run.py
```

此前发布的短日志及其对应源码保留在 [earlier-capture](earlier-capture/)，供核对历史记录。其 `Matches expectation: true` 表示结果符合对照预期，绝不表示错误例子编译成功；新的结果文件直接记录 `FAILED` 或 `SUCCEEDED`。
