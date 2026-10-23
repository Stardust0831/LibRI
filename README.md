# OpenMP collapse: GCC 13.3 compilation evidence

Moving element declarations into the innermost loop allows the indexed
`collapse(2)` example to compile with GCC 13.3 and OpenMP enabled.

This reproduces the loop structure discussed for LibRI's
[`fac_add_Ds` commit fe27bb1](https://gitee.com/linpeize/LibRI/commit/fe27bb14d9abbccd9d05296a0833278acc7f34f4),
in connection with [LibRI #15](https://github.com/abacusmodeling/LibRI/pull/15).

| Source | GCC 13.3 result |
| --- | --- |
| [range_for.cpp](range_for.cpp): nested range-based loops | Compiles |
| [intervening_declaration.cpp](intervening_declaration.cpp): indexed loops with a declaration between the two loop levels | Fails: `not enough for loops to collapse` |
| [declarations_innermost.cpp](declarations_innermost.cpp): indexed loops with both declarations inside the inner loop | Compiles |

The [complete compilation log](compilation.log) records the compiler version,
commands, standard output, standard error, exit codes and object-file checks.
Successful GCC compilation normally produces no diagnostic output; the log
explicitly records exit code `0` and confirms that an object file was generated.

Run with Python 3 and GCC:

```sh
python3 run.py
```

Each source is compiled using `g++ -std=c++17 -fopenmp -c`. The runner uses a
temporary build directory and writes `compilation.log` next to the sources.
Its exit status checks all three expected outcomes, including rejection of
the middle example. These expectations apply to the recorded GCC 13.3 toolchain;
other compilers may support additional OpenMP constructs.

This is a minimal compilation check. It does not establish that all modified
LibRI headers compile or that numerical calculations pass. No fixed full-LibRI
build is claimed by this log.
