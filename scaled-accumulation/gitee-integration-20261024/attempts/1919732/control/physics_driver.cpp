#include <RI/ri/LRI.h>
#include <RI/ri/Label_Tools.h>
#include <RI/physics/Exx.h>
#include <algorithm>
#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#include <mpi.h>

#ifdef TEST_COMPLEX
using Scalar = std::complex<TEST_REAL>;
#else
using Scalar = TEST_REAL;
#endif
using Real = TEST_REAL;
template<std::size_t N> using Maps = std::map<int,
    std::map<std::pair<int, std::array<int,N>>, RI::Tensor<Scalar>>>;

struct Metrics
{
    std::size_t elements = 0;
    double max_absolute = 0;
    double max_scaled = 0;
    void check(const Scalar actual, const Scalar expected, const double scale,
               const std::string& context)
    {
        const double error = std::abs(actual - expected);
        const double scaled = error / scale;
        if(!std::isfinite(error) || scaled > 256 * std::numeric_limits<Real>::epsilon())
        {
            std::cerr << context << " actual=" << actual << " expected=" << expected
                      << " error=" << error << " scale=" << scale << std::endl;
            throw std::runtime_error("Numerical comparison failed");
        }
        ++elements;
        max_absolute = std::max(max_absolute, error);
        max_scaled = std::max(max_scaled, scaled);
    }
    void print(const std::string& name, const RI::LRI_Cal_Mode mode) const
    {
        std::cout << "PASS " << name << " mode=" << static_cast<int>(mode)
                  << " elements=" << elements << " max_abs=" << max_absolute
                  << " max_scaled=" << max_scaled << std::endl;
    }
};

RI::Tensor<Scalar> make_tensor(const RI::Shape_Vector& shape, const int salt)
{
    RI::Tensor<Scalar> result(shape);
    for(std::size_t i = 0; i < result.data->size(); ++i)
    {
        const double x = static_cast<double>(i + 1);
        (*result.data)[i] = RI::Global_Func::convert<Scalar>(std::complex<Real>(
            0.3 + 0.21*std::sin(0.73*x + salt), 0.07*std::cos(0.37*x + 0.2*salt)));
    }
    return result;
}

template<std::size_t N>
Maps<N> clone(const Maps<N>& input)
{
    Maps<N> output;
    for(const auto& a : input)
        for(const auto& b : a.second)
            output[a.first][b.first] = b.second.copy();
    return output;
}

template<std::size_t N>
void check_maps(const Maps<N>& actual, const Maps<N>& expected, Metrics& metrics,
                const std::string& context)
{
    if(actual.size() != expected.size())
        throw std::runtime_error(context + ": wrong outer map size");
    for(const auto& a : expected)
    {
        if(actual.at(a.first).size() != a.second.size())
            throw std::runtime_error(context + ": wrong inner map size");
        for(const auto& b : a.second)
        {
            const auto& test = actual.at(a.first).at(b.first);
            const auto& ref = b.second;
            if(!std::equal(test.shape.begin(), test.shape.end(), ref.shape.begin(), ref.shape.end()))
                throw std::runtime_error(context + ": wrong tensor shape");
            for(std::size_t i = 0; i < ref.data->size(); ++i)
                metrics.check((*test.data)[i], (*ref.data)[i],
                    1 + std::abs((*ref.data)[i]), context);
        }
    }
}

// The reference sum is formed element by element, without LibRI's accumulation helpers.
void check_accumulation(const RI::LRI_Cal_Mode mode, const bool multiple_atoms)
{
    using LRI = RI::LRI<int,int,1,Scalar>;
    const auto labels = RI::Global_Func::to_vector(RI::Label::array_ab_ab);
    const int atoms = multiple_atoms ? 2 : 1;
    const int cells = multiple_atoms ? 2 : 1;
    std::map<int, std::array<double,1>> positions;
    for(int a = 0; a < atoms; ++a)
        positions[a] = {0.4*a};
    LRI lri;
    lri.set_parallel(MPI_COMM_SELF, positions, {{{1.0}}}, {cells}, labels);
    for(const auto label : RI::Label::array_ab)
    {
        Maps<1> input;
        for(int a = 0; a < atoms; ++a)
            for(int b = 0; b < atoms; ++b)
                for(int c = 0; c < cells; ++c)
                {
                    const std::size_t na = 2+a, nb = 2+b;
                    const bool coefficient = label == RI::Label::ab::a || label == RI::Label::ab::b;
                    input[a][{b,{c}}] = make_tensor(
                        coefficient ? RI::Shape_Vector{na,na,nb} : RI::Shape_Vector{na,nb},
                        17*a + 7*b + 3*c + static_cast<int>(label));
                }
        lri.set_tensors_map2(input, {label});
    }
    std::vector<std::vector<RI::Label::ab_ab>> groups;
    if(!multiple_atoms)
        for(const auto label : labels)
            groups.push_back({label});
    else
    {
        groups.push_back(labels);
        groups.push_back({RI::Label::ab_ab::a0b0_a1b1, RI::Label::ab_ab::a0b0_a1b2,
                          RI::Label::ab_ab::a0b0_a2b1, RI::Label::ab_ab::a0b0_a2b2});
        // Duplicate labels deliberately exercise repeated writes to the same blocks.
        groups.push_back({labels.front(), labels.back(), labels.front()});
    }
    Metrics metrics;
    for(const auto& group : groups)
    {
        Maps<1> contribution;
        lri.cal_mode = RI::LRI_Cal_Mode::CPU;
        for(const auto label : group)
        {
            Maps<1> single;
            lri.cal_loop3({label}, single);
            for(const auto& a : single)
                for(const auto& b : a.second)
                {
                    auto& sum = contribution[a.first][b.first];
                    if(sum.empty())
                        sum = RI::Tensor<Scalar>(b.second.shape);
                    for(std::size_t i = 0; i < sum.data->size(); ++i)
                        (*sum.data)[i] += (*b.second.data)[i];
                }
        }
        if(contribution.empty())
            throw std::runtime_error("Empty CPU reference");
        for(const auto& a : contribution)
            for(const auto& b : a.second)
                if(!std::isfinite(b.second.norm(2)) || b.second.norm(2) == 0)
                    throw std::runtime_error("Invalid CPU reference");
        lri.cal_mode = mode;
        for(const bool seeded : {false, true})
        {
            Maps<1> seed;
            if(seeded)
                for(const auto& a : contribution)
                    for(const auto& b : a.second)
                        seed[a.first][b.first] = make_tensor(b.second.shape, 13+a.first);
            Maps<1> actual = clone(seed);
            Real factor_sum = 0, factor_abs_sum = 0;
            for(const double factor : {0.0, -1.0, 1.0, 1.0, -1.0, 0.5, 0.0, -0.5, 0.3})
            {
                lri.cal_loop3(group, actual, factor);
                factor_sum += Real(factor);
                factor_abs_sum += std::abs(Real(factor));
                const std::string context = "accumulation " + RI::Label_Tools::get_name(group)
                    + " seeded=" + std::to_string(seeded) + " factor=" + std::to_string(factor);
                if(actual.size() != contribution.size())
                    throw std::runtime_error(context + ": wrong outer map size");
                for(const auto& a : contribution)
                {
                    if(actual.at(a.first).size() != a.second.size())
                        throw std::runtime_error(context + ": wrong inner map size");
                    for(const auto& b : a.second)
                    {
                        const auto& test = actual.at(a.first).at(b.first);
                        if(!std::equal(test.shape.begin(), test.shape.end(), b.second.shape.begin(), b.second.shape.end()))
                            throw std::runtime_error(context + ": wrong tensor shape");
                        for(std::size_t i = 0; i < test.data->size(); ++i)
                        {
                            const Scalar initial = seeded ? (*seed.at(a.first).at(b.first).data)[i] : Scalar(0);
                            const Scalar term = (*b.second.data)[i];
                            const Scalar expected = initial + factor_sum*term;
                            metrics.check((*test.data)[i], expected,
                                1 + std::abs(initial) + factor_abs_sum*std::abs(term), context);
                        }
                    }
                }
            }
            const auto saved = clone(actual);
            lri.cal_loop3({}, actual, -1);
            check_maps(actual, saved, metrics, "empty label list");
        }
    }
    metrics.print(multiple_atoms ? "multiatom-periodic-groups" : "all-18-contractions", mode);
}

using Exx = RI::Exx<int,int,3,Scalar>;

void setup_exx(Exx& exx, const RI::LRI_Cal_Mode mode, const double density_scale)
{
    exx.lri.cal_mode = mode;
    exx.flag_save_result.dHs = true;
    exx.flag_save_result.dHRs = true;
    exx.set_parallel(MPI_COMM_SELF, {{0,{0,0,0}}, {1,{0.4,0.2,0.3}}},
                     {{{1,0,0},{0,1,0},{0,0,1}}}, {1,1,1});
    exx.set_symmetry(false, {});
    Maps<3> cs, vs, ds;
    std::array<Maps<3>,3> dcs, dvs;
    std::array<std::array<Maps<3>,3>,3> dcrs, dvrs;
    for(int a = 0; a < 2; ++a)
        for(int b = 0; b < 2; ++b)
        {
            const Exx::TAC key = {b,{0,0,0}};
            const RI::Shape_Vector cshape{std::size_t(3+a),std::size_t(2+a),std::size_t(2+b)};
            const RI::Shape_Vector vshape{std::size_t(3+a),std::size_t(3+b)};
            cs[a][key] = make_tensor(cshape, 19*a+7*b);
            vs[a][key] = make_tensor(vshape, 11*a+3*b+2);
            ds[a][key] = Scalar(density_scale) * make_tensor(
                {std::size_t(2+a),std::size_t(2+b)}, 7*a+5*b+11);
            for(int p = 0; p < 3; ++p)
            {
                dcs[p][a][key] = Scalar(p%2 ? -0.2 : 0.3) * make_tensor(cshape, 13*a+17*b+5*p+3);
                dvs[p][a][key] = Scalar(p%2 ? 0.15 : -0.25) * make_tensor(vshape, 3*a+11*b+7*p+5);
                for(int q = 0; q < 3; ++q)
                {
                    dcrs[p][q][a][key] = Scalar(0.1*(p+1)-0.15*(q+1)) * make_tensor(cshape, 17*a+13*b+3*p+5*q);
                    dvrs[p][q][a][key] = Scalar(0.2*(p+1)-0.1*(q+1)) * make_tensor(vshape, 7*a+11*b+5*p+3*q);
                }
            }
        }
    exx.set_Cs(cs, 0);
    exx.set_Vs(vs, 0);
    exx.set_Ds(ds, 0);
    exx.set_dCs(dcs, 0);
    exx.set_dVs(dvs, 0);
    exx.set_dCRs(dcrs, 0);
    exx.set_dVRs(dvrs, 0);
}

void check_exx(const RI::LRI_Cal_Mode mode)
{
    Exx reference, test;
    setup_exx(reference, RI::LRI_Cal_Mode::CPU, 1.0);
    setup_exx(test, mode, 1.0);
    reference.cal_Hs();
    test.cal_Hs();
    Metrics hs, energy, dhs, forces, dhrs, stress;
    check_maps(test.Hs, reference.Hs, hs, "Exx Hs");
    energy.check(test.energy, reference.energy, 1+std::abs(reference.energy), "Exx energy");
    reference.cal_force();
    test.cal_force();
    double force_norm = 0;
    for(int p = 0; p < 3; ++p)
    {
        for(int side = 0; side < 2; ++side)
            check_maps(test.dHs[p][side], reference.dHs[p][side], dhs, "Exx dHs");
        if(test.force[p].size() != reference.force[p].size())
            throw std::runtime_error("Exx force map size mismatch");
        for(const auto& f : reference.force[p])
        {
            forces.check(test.force[p].at(f.first), f.second, 1+std::abs(f.second), "Exx force");
            force_norm += std::abs(f.second);
        }
    }
    if(force_norm == 0 || !std::isfinite(force_norm))
        throw std::runtime_error("Force fixture is trivial or invalid");
    reference.cal_stress();
    test.cal_stress();
    for(int p = 0; p < 3; ++p)
        for(int q = 0; q < 3; ++q)
        {
            check_maps(test.dHRs[p][q], reference.dHRs[p][q], dhrs, "Exx dHRs");
            stress.check(test.stress(p,q), reference.stress(p,q),
                         1+std::abs(reference.stress(p,q)), "Exx stress");
        }
    hs.print("Exx-Hs", mode);
    energy.print("Exx-energy", mode);
    dhs.print("Exx-dHs", mode);
    forces.print("Exx-force", mode);
    dhrs.print("Exx-dHRs", mode);
    stress.print("Exx-stress", mode);

    // Exercise existing Hs accumulation with a changed density matrix.
    Exx updated;
    setup_exx(updated, RI::LRI_Cal_Mode::CPU, 0.85);
    Maps<3> new_density;
    for(int a = 0; a < 2; ++a)
        for(int b = 0; b < 2; ++b)
            new_density[a][{b,{0,0,0}}] = Scalar(0.85) * make_tensor(
                {std::size_t(2+a),std::size_t(2+b)}, 7*a+5*b+11);
    test.set_Ds_delta(new_density, 0);
    test.cal_Hs();
    updated.cal_Hs();
    Metrics delta;
    check_maps(test.Hs, updated.Hs, delta, "Exx delta-density Hs");
    delta.check(test.energy, updated.energy, 1+std::abs(updated.energy), "Exx delta-density energy");
    delta.print("Exx-density-update", mode);
}

#include "unequal_dimensions.hpp"

int main(int argc, char** argv)
{
    int provided = 0;
    if(MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &provided) != MPI_SUCCESS)
        return 1;
    int status = 0;
    try
    {
        int ranks = 0;
        MPI_Comm_size(MPI_COMM_WORLD, &ranks);
        if(ranks != 1 || provided < MPI_THREAD_MULTIPLE)
            throw std::runtime_error("Test requires one MPI rank and MPI_THREAD_MULTIPLE");
        std::cout << std::setprecision(17);
        const std::string suite = argc > 1 ? argv[1] : "all";
        for(const auto mode : {RI::LRI_Cal_Mode::CPU, RI::LRI_Cal_Mode::CPU_fine_grained_lock,
#ifdef __GPU_RI
                              RI::LRI_Cal_Mode::GPU,
#endif
                             })
        {
            if(suite != "physics")
            {
                check_accumulation(mode, false);
                check_accumulation(mode, true);
                LRI_Loop3_Test::test_loop3<Scalar>(mode);
            }
            if(suite != "contractions")
                check_exx(mode);
        }
    }
    catch(const std::exception& error)
    {
        std::cerr << error.what() << std::endl;
        status = 1;
    }
    MPI_Finalize();
    return status;
}
