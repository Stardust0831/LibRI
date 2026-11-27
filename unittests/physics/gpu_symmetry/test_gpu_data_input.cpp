#include <RI/ri/LRI.h>

#include <algorithm>
#include <array>
#include <complex>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
template <typename T>
RI::Tensor<T> make_tensor(const RI::Shape_Vector& shape, T imaginary)
{
    RI::Tensor<T> tensor(shape);
    const std::size_t size = shape.get_shape_all();
    for (std::size_t i = 0; i < size; ++i)
        tensor.ptr()[i] = T(0.01 * (i + 1)) + imaginary * T(0.003 * (i + 2));
    return tensor;
}

void require(bool condition, const char* message)
{
    if (!condition)
        throw std::runtime_error(message);
}

template <typename T>
void check_packing(T imaginary, RI::GPU_Backend::Queue queue)
{
    using Device = RI::GPU_Backend::Type_to_GPU<T>;
    RI::GPU_Data::Input<int, int, T> packed;
    RI::GPU_Data::Input<int, int, T> reference;
    const std::vector<RI::Shape_Vector> shapes{{2, 3, 4}, {5, 1, 2}, {1, 4, 1}};
    std::vector<RI::Tensor<T>> tensors;
    for (const RI::Shape_Vector& shape : shapes)
        tensors.push_back(make_tensor(shape, imaginary));

    // As in cal_loop3_GPU, metadata insertion is serialized and payload packing
    // uses the inserting thread's buffer. Repeated keys must not copy twice.
    #pragma omp parallel for schedule(static)
    for (int i = 0; i < 12; ++i)
    {
        const int key = i % 3;
        const RI::Tensor<T>& tensor = tensors[key];
        #pragma omp critical(test_input_metadata)
        packed.insert_transpose(0, key, tensor);
        packed.insert_data_transpose(tensor);
    }
    std::size_t packed_size = 0;
    for (const std::vector<Device>& buffer : packed.h_data)
        packed_size += buffer.size();
    require(packed_size == 38, "Duplicate tensor payload was packed");
    require(packed.h_array.size() == 12, "Repeated batch entries were lost");

    packed.upload(queue);
    std::vector<Device*> device_pointers(packed.h_array.size());
    RI::GPU_Backend::download(device_pointers.size(), packed.d_array, device_pointers.data(), queue);
    RI::GPU_Backend::sync(queue);
    for (int key = 0; key < 3; ++key)
    {
        const RI::Tensor<T>& original = tensors[key];
        const RI::Tensor<T> transposed = RI::LRI_Cal_Aux::tensor3_transpose(original);
        const RI::GPU_Data::Pack expected_pack = reference.insert(0, key, transposed);
        reference.insert_data(transposed);
        const RI::GPU_Data::Pack& actual_pack = packed.ptrList.at(0).at(key);
        require(std::equal(transposed.shape.begin(), transposed.shape.end(), actual_pack.shape.begin()),
                "Transposed shape differs");
        const std::vector<Device>& expected = reference.h_data[0];
        const std::vector<Device>& actual = packed.h_data[actual_pack.thread_num];
        const std::size_t size = transposed.shape.get_shape_all();
        for (std::size_t batch = 0; batch < packed.h_array.size(); ++batch)
        {
            const RI::GPU_Data::Pack& entry = packed.h_array[batch];
            if (entry.thread_num != actual_pack.thread_num || entry.pos != actual_pack.pos)
                continue;
            std::vector<Device> downloaded(size);
            RI::GPU_Backend::download(size, device_pointers[batch], downloaded.data(), queue);
            RI::GPU_Backend::sync(queue);
            for (std::size_t i = 0; i < size; ++i)
            {
                require(actual[actual_pack.pos + i] == expected[expected_pack.pos + i], "Host packing differs");
                require(downloaded[i] == expected[expected_pack.pos + i], "Uploaded payload differs");
            }
        }
        const RI::Tensor<T> unchanged = make_tensor(original.shape, imaginary);
        for (std::size_t i = 0; i < size; ++i)
            require(original.ptr()[i] == unchanged.ptr()[i], "Packing modified its input");
    }

    RI::GPU_Data::Input<int, int, T> empty;
    for (const RI::Shape_Vector& shape : {RI::Shape_Vector{0, 3, 2},
                                         RI::Shape_Vector{2, 0, 3}, RI::Shape_Vector{3, 2, 0}})
    {
        const RI::Tensor<T> tensor(shape);
        const int key = static_cast<int>(empty.h_array.size());
        empty.insert_transpose(0, key, tensor);
        empty.insert_data_transpose(tensor);
    }
    require(empty.h_data[0].empty(), "Zero-sized tensor added payload");
}

template <typename T>
void check_contractions(T imaginary, bool share_coefficients)
{
    using Cell = std::array<int, 1>;
    using Blocks = std::map<int, std::map<std::pair<int, Cell>, RI::Tensor<T>>>;
    RI::LRI<int, int, 1, T> lri;
    const std::map<int, std::array<double, 1>> atoms{{0, {0.0}}};
    const std::array<std::array<double, 1>, 1> lattice{{{{1.0}}}};
    const Cell period{{1}};
    const std::vector<RI::Label::ab_ab> labels(RI::Label::array_ab_ab.begin(), RI::Label::array_ab_ab.end());
    lri.set_parallel(MPI_COMM_WORLD, atoms, lattice, period, labels);
    const RI::Shape_Vector a{2, 3, 4};
    const RI::Shape_Vector b = share_coefficients ? a : RI::Shape_Vector{5, 6, 7};
    for (const RI::Label::ab label : RI::Label::array_ab)
    {
        if (share_coefficients && label == RI::Label::ab::b)
            continue;
        RI::Shape_Vector shape;
        if (label == RI::Label::ab::a)
            shape = a;
        else if (label == RI::Label::ab::b)
            shape = b;
        else
        {
            const std::string name = RI::Label_Tools::get_name(label);
            shape = {a[name[1] - '0'], b[name[3] - '0']};
        }
        Blocks tensors;
        tensors[0][{0, {0}}] = make_tensor(shape, imaginary);
        std::vector<RI::Label::ab> tensor_labels{label};
        if (share_coefficients && label == RI::Label::ab::a)
            tensor_labels.push_back(RI::Label::ab::b);
        lri.set_tensors_map2(tensors, tensor_labels);
    }
    double max_error = 0;
    for (const RI::Label::ab_ab label : labels)
    {
        Blocks expected;
        Blocks actual;
        lri.cal_mode = RI::LRI_Cal_Mode::CPU;
        lri.cal_loop3({label}, expected, 1.0);
        lri.cal_mode = RI::LRI_Cal_Mode::GPU;
        lri.cal_loop3({label}, actual, 1.0);
        const RI::Tensor<T>& cpu = expected.at(0).at({0, {0}});
        const RI::Tensor<T>& gpu = actual.at(0).at({0, {0}});
        require(cpu.shape.size() == gpu.shape.size(), "Contraction rank differs");
        require(std::equal(cpu.shape.begin(), cpu.shape.end(), gpu.shape.begin()), "Contraction shape differs");
        for (std::size_t i = 0; i < cpu.shape.get_shape_all(); ++i)
        {
            const double error = std::abs(cpu.ptr()[i] - gpu.ptr()[i]);
            max_error = std::max(max_error, error);
            require(error <= 1e-11 * (1.0 + std::abs(cpu.ptr()[i])), "Nonsquare contraction differs from CPU");
        }
    }
    std::cout << "PASS all 18 nonsquare contractions; shared=" << share_coefficients
              << " max_abs_error=" << max_error << '\n';
}
} // namespace

int main(int argc, char** argv)
{
    int provided = 0;
    if (MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &provided) != MPI_SUCCESS)
        return 1;
    int status = 0;
    try
    {
        require(RI::MPI_Wrapper::mpi_get_size(MPI_COMM_WORLD) == 1, "One MPI rank required");
        require(provided >= MPI_THREAD_MULTIPLE, "MPI_THREAD_MULTIPLE required");
        {
            RI::GPU_Backend::Context context(MPI_COMM_WORLD);
            check_packing<float>(0.0f, context.queue());
            check_packing<double>(0.0, context.queue());
            check_packing<std::complex<float>>({0.0f, 1.0f}, context.queue());
            check_packing<std::complex<double>>({0.0, 1.0}, context.queue());
        }
        for (const bool shared : {false, true})
        {
            check_contractions<double>(0.0, shared);
            check_contractions<std::complex<double>>({0.0, 1.0}, shared);
        }
        std::cout << "PASS transpose packing, threads=" << omp_get_max_threads() << '\n';
    }
    catch (const std::exception& error)
    {
        std::cerr << error.what() << '\n';
        status = 1;
    }
    MPI_Finalize();
    return status;
}
