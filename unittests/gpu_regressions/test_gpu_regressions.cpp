#include <RI/ri/LRI.h>
#include <RI/ri/Label_Tools.h>

#include <mpi.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
#ifdef TEST_COMPLEX
using Scalar = std::complex<double>;
Scalar value(double real, double imaginary) { return {real, imaginary}; }
#else
using Scalar = double;
Scalar value(double real, double) { return real; }
#endif
using Lri = RI::LRI<int, int, 1, Scalar>;
using Label = RI::Label::ab;
using Contraction = RI::Label::ab_ab;
using Tensors = std::map<int, std::map<Lri::TAC, RI::Tensor<Scalar>>>;

const std::vector<Contraction> contractions{
    Contraction::a0b0_a1b1, Contraction::a0b0_a1b2,
    Contraction::a0b0_a2b1, Contraction::a0b0_a2b2};

bool coefficient(Label label) { return label == Label::a || label == Label::b; }
std::string name(Label label) { return RI::Label_Tools::get_name(label); }

void compare(const Tensors& actual, const Tensors& expected, const std::string& context)
{
    int local_failed = 0;
    double local_max_error = 0;
    try
    {
        if (actual.size() != expected.size())
            throw std::runtime_error("output atom count differs");
        for (const auto& row : expected)
        {
            if (actual.at(row.first).size() != row.second.size())
                throw std::runtime_error("output block count differs");
            for (const auto& block : row.second)
            {
                const auto& result = actual.at(row.first).at(block.first);
                const auto& reference = block.second;
                if (result.shape.size() != reference.shape.size()
                    || !std::equal(result.shape.begin(), result.shape.end(), reference.shape.begin()))
                    throw std::runtime_error("output shape differs");
                for (std::size_t i = 0; i < reference.data->size(); ++i)
                {
                    const Scalar expected_value = (*reference.data)[i];
                    const double error = std::abs((*result.data)[i] - expected_value);
                    local_max_error = std::max(local_max_error, error);
                    const double tolerance = 256 * std::numeric_limits<double>::epsilon()
                                             * (1 + std::abs(expected_value));
                    if (!std::isfinite(error) || error > tolerance)
                    {
                        if (!local_failed)
                            std::cerr << context << " actual=" << (*result.data)[i]
                                      << " expected=" << expected_value << " error=" << error
                                      << " tolerance=" << tolerance << '\n';
                        local_failed = 1;
                    }
                }
            }
        }
    }
    catch (const std::exception& error)
    {
        std::cerr << context << ": " << error.what() << '\n';
        local_failed = 1;
    }
    int failed = 0;
    double max_error = 0;
    MPI_Allreduce(&local_failed, &failed, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    MPI_Allreduce(&local_max_error, &max_error, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
    int rank = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    if (rank == 0)
        std::cout << (failed ? "FAIL " : "PASS ") << context
                  << " max_abs_error=" << max_error << std::endl;
    if (failed)
        throw std::runtime_error("GPU result differs from the independent CPU calculation");
}

void check(Lri& lri, const std::string& context)
{
    Tensors cpu, gpu;
    lri.cal_mode = RI::LRI_Cal_Mode::CPU;
    lri.cal_loop3(contractions, cpu);
    lri.cal_mode = RI::LRI_Cal_Mode::GPU;
    lri.cal_loop3(contractions, gpu);
    compare(gpu, cpu, context);
}

void residency(Lri& lri, bool enabled)
{
    lri.set_gpu_resident_data_names(enabled ? std::set<std::string>{"a", "b", "a0b0"}
                                          : std::set<std::string>{});
}

Tensors one(bool three_indices, Scalar number)
{
    Tensors result;
    auto& tensor = result[0][{0, {0}}];
    tensor = RI::Tensor<Scalar>(three_indices ? RI::Shape_Vector{1, 1, 1}
                                            : RI::Shape_Vector{1, 1});
    (*tensor.data)[0] = number;
    return result;
}

// Supply exactly C_a, C_b, and the two input maps named by each contraction.
// The CPU calculation establishes that omitting all other maps is valid.
void minimal(bool resident)
{
    int failures = 0;
    for (const auto label : RI::Label::array_ab_ab)
    {
        const std::string label_name = RI::Label_Tools::get_name(label);
        try
        {
            Lri lri;
            lri.set_parallel(MPI_COMM_WORLD, {{0, {0.0}}}, {{{1.0}}}, {1}, {label});
            lri.set_tensors_map2(one(true, value(2, 0.1)), {Label::a});
            lri.set_tensors_map2(one(true, value(3, -0.2)), {Label::b});
            const auto separator = label_name.find('_');
            for (const auto input : RI::Label::array_ab)
                if (name(input) == label_name.substr(0, separator)
                    || name(input) == label_name.substr(separator + 1))
                    lri.set_tensors_map2(one(false, value(4, 0.3)), {input});
            residency(lri, resident);
            Tensors cpu, gpu;
            lri.cal_mode = RI::LRI_Cal_Mode::CPU;
            lri.cal_loop3({label}, cpu);
            if (cpu.empty())
                throw std::runtime_error("empty CPU reference");
            std::cout << "CPU_REFERENCE_OK " << label_name << std::endl;
            lri.cal_mode = RI::LRI_Cal_Mode::GPU;
            lri.cal_loop3({label}, gpu);
            compare(gpu, cpu, label_name);
        }
        catch (const std::exception& error)
        {
            ++failures;
            std::cout << "FAIL " << label_name << " exception=" << error.what() << std::endl;
        }
    }
    std::cout << "minimal failures=" << failures << "/18" << std::endl;
    if (failures)
        throw std::runtime_error("minimal-input contractions failed");
}

Tensors data(Label label, int salt)
{
    Tensors result;
    for (int a = 0; a < 2; ++a)
        for (int b = 0; b < 2; ++b)
            for (int cell = 0; cell < 2; ++cell)
            {
                const std::size_t na = 2 + a, nb = 2 + b;
                auto& tensor = result[a][{b, {cell}}];
                tensor = RI::Tensor<Scalar>(coefficient(label) ? RI::Shape_Vector{na, na, nb}
                                                               : RI::Shape_Vector{na, nb});
                const int phase = 17 * a + 7 * b + 3 * cell + int(label) + salt;
                for (std::size_t i = 0; i < tensor.data->size(); ++i)
                {
                    const double x = double(i + 1);
                    (*tensor.data)[i] = value(0.3 + 0.21 * std::sin(0.73 * x + phase),
                                             0.07 * std::cos(0.37 * x + 0.2 * phase));
                }
            }
    return result;
}

void replace(Lri& lri, Label label, int salt)
{
    lri.set_tensors_map2(data(label, salt), {label}, {}, name(label));
}

void initialize(Lri& lri, bool resident)
{
    lri.set_parallel(MPI_COMM_WORLD, {{0, {0.0}}, {1, {0.4}}}, {{{1.0}}}, {2}, contractions);
    for (const auto label : RI::Label::array_ab)
        replace(lri, label, 0);
    residency(lri, resident);
}

// Warm A, copy A to B, replace data in B, then evaluate B before A. Reversing
// the last two evaluations can hide the bug by uploading A's tensors first.
void copied(bool resident, const std::string& scenario)
{
    Lri first;
    initialize(first, resident);
    check(first, "original-warm");
    Lri second = first;
    if (scenario == "assignment")
    {
        Lri replacement;
        initialize(replacement, resident);
        replace(replacement, Label::a, 11);
        check(replacement, "assignment-old-state");
        replacement = first;
        second = std::move(replacement);
    }
    if (scenario == "density")
    {
        for (const auto label : {Label::a1b1, Label::a1b2, Label::a2b1, Label::a2b2})
            replace(second, label, 43);
        check(second, "copy-new-D");
        check(first, "original-after-D");
        return;
    }
    if (scenario == "free_reload")
    {
        second.free_tensors_map2(name(Label::a));
        check(first, "original-after-copy-free");
    }
    replace(second, scenario == "copy_v" ? Label::a0b0 : Label::a, 41);
    check(second, "copy-new-C-or-V");
    check(first, "original-after-copy-update");
    replace(first, Label::b, 47);
    check(first, "original-new-Cb");
    check(second, "copy-after-original-update");
}

// Only rank zero retains a copy. Detaching the cache must not construct a new
// context: its MPI setup is collective, but cache reference counts are local.
void asymmetric(bool resident)
{
    int rank = 0, size = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (size < 2)
        throw std::runtime_error("asymmetric test needs at least two MPI ranks");
    Lri first;
    initialize(first, resident);
    check(first, "asymmetric-warm");
    std::unique_ptr<Lri> backup;
    if (rank == 0)
        backup.reset(new Lri(first));
    replace(first, Label::a, 53);
    check(first, "asymmetric-C-update");
    first.free_tensors_map2(name(Label::a0b0));
    replace(first, Label::a0b0, 59);
    check(first, "asymmetric-V-free-reload");
}
} // namespace

int main(int argc, char** argv)
{
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &provided);
    int status = 0;
    std::cout << std::setprecision(17);
    std::cerr << std::setprecision(17);
    try
    {
        if (argc != 3 || (std::string(argv[2]) != "on" && std::string(argv[2]) != "off"))
            throw std::runtime_error("usage: gpu_regressions_{real,complex} SCENARIO {on,off}");
        const std::string scenario = argv[1];
        const bool resident = std::string(argv[2]) == "on";
        if (scenario == "minimal")
            minimal(resident);
        else if (scenario == "asymmetric")
            asymmetric(resident);
        else if (scenario == "copy_c" || scenario == "copy_v" || scenario == "assignment"
                 || scenario == "free_reload" || scenario == "density")
            copied(resident, scenario);
        else
            throw std::runtime_error("unknown scenario: " + scenario);
    }
    catch (const std::exception& error)
    {
        std::cerr << "FAIL " << error.what() << std::endl;
        status = 1;
    }
    MPI_Finalize();
    return status;
}
