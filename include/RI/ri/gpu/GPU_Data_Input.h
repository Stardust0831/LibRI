// =================================
//  Author: Laiyuan Yang, Peize Lin
//  date: 2026.01.01
// =================================

#pragma once

#ifdef __GPU_RI

#include "../../global/gpu/GPU_Backend.h"
#include "GPU_Data_Pack.h"

#include <cassert>
#include <cstring>
#include <omp.h>
#include <type_traits>
#include <utility>

namespace RI
{

namespace GPU_Data
{

template<typename TA, typename TAC, typename Tdata_CPU>
class Input
{
  public:
	GPU_Backend::Queue queue_ = nullptr;
	using Tdata_GPU = GPU_Backend::Type_to_GPU<Tdata_CPU>;
	using Same_data_layout = std::integral_constant<
		bool,
		sizeof(Tdata_CPU)==sizeof(Tdata_GPU) && alignof(Tdata_CPU)==alignof(Tdata_GPU)>;

	Input()
	{
		this->h_data.resize(omp_get_max_threads());
		this->tensor_insert.resize(omp_get_max_threads(), false);
	}

	const Pack & insert(const TA &Aa, const TAC &Ab, const Tensor<Tdata_CPU> &tensor)
	{
		return this->insert_shape(Aa, Ab, tensor.shape);
	}

	// Pack the first two axes in reverse order without an intermediate Tensor.
	const Pack & insert_transpose(const TA &Aa, const TAC &Ab, const Tensor<Tdata_CPU> &tensor)
	{
		assert(tensor.shape.size() == 3);
		Shape_Vector shape = tensor.shape;
		std::swap(shape[0], shape[1]);
		return this->insert_shape(Aa, Ab, shape);
	}

  private:
	const Pack & insert_shape(const TA &Aa, const TAC &Ab, const Shape_Vector &shape)
	{
		Pack &pack = this->ptrList[Aa][Ab];
		if(!pack.exist)
		{
			pack.exist = true;
			pack.pos = this->h_data[omp_get_thread_num()].size();
			this->tensor_insert[omp_get_thread_num()] = true;
			pack.shape = shape;
			pack.thread_num = omp_get_thread_num();
		}
		else
		{
			this->tensor_insert[omp_get_thread_num()] = false;
		}
		this->h_array.push_back(pack);
		return pack;
	}

  public:
	void insert_data(const Tensor<Tdata_CPU> &tensor)
	{
		const int thread_num = omp_get_thread_num();
		if(this->tensor_insert[thread_num])
			insert_data_impl(this->h_data[thread_num], tensor, Same_data_layout());
	}

	void insert_data_transpose(const Tensor<Tdata_CPU> &tensor)
	{
		const int thread_num = omp_get_thread_num();
		if (!this->tensor_insert[thread_num])
			return;
		assert(tensor.shape.size() == 3);
		std::vector<Tdata_GPU> &buffer = this->h_data[thread_num];
		const std::size_t begin = buffer.size();
		const std::size_t size = tensor.shape.get_shape_all();
		buffer.resize(begin + size);
		const std::size_t row_size = tensor.shape[2];
		if (size == 0)
			return;
		for (std::size_t i1 = 0; i1 < tensor.shape[1]; ++i1)
			for (std::size_t i0 = 0; i0 < tensor.shape[0]; ++i0)
			{
				const std::size_t source_offset = (i0 * tensor.shape[1] + i1) * row_size;
				const std::size_t target_offset = begin + (i1 * tensor.shape[0] + i0) * row_size;
				const Tdata_CPU *source = tensor.ptr() + source_offset;
				Tdata_GPU *target = buffer.data() + target_offset;
				copy_row(target, source, row_size, Same_data_layout());
			}
	}

	// 将对应的 C, V, D 放在 d_Cs, d_Vs, d_Ds 上
	void upload(GPU_Backend::Queue queue)
	{
		this->queue_ = queue;
		std::vector<std::size_t> h_data_begin(this->h_data.size()+1, 0);
		for(std::size_t i=1; i<h_data_begin.size(); ++i)
			h_data_begin[i] = h_data_begin[i-1] + this->h_data[i-1].size();

		GPU_Backend::allocate(&this->d_data, h_data_begin.back(), queue);
		for(std::size_t i=0; i<this->h_data.size(); ++i)
			GPU_Backend::upload(
				this->h_data[i].size(), this->h_data[i].data(),
				this->d_data+h_data_begin[i], queue);

		const std::size_t batchCount = this->h_array.size();
		std::vector<Tdata_GPU*> d_array_(batchCount);							// 记录每个batch的 d_data 指针（CPU）
		for(std::size_t i=0; i<batchCount; ++i)
			d_array_[i] = this->d_data + this->h_array[i].pos + h_data_begin[this->h_array[i].thread_num];
		GPU_Backend::allocate(&this->d_array, batchCount, queue);
		GPU_Backend::upload(batchCount, d_array_.data(), this->d_array, queue);
	}

	~Input()
	{
		GPU_Backend::free(this->d_data, this->queue_);
		GPU_Backend::free(this->d_array, this->queue_);
	}

  private:
	static void copy_row(Tdata_GPU *target, const Tdata_CPU *source,
	                     const std::size_t size, std::true_type)
	{
		std::memcpy(target, source, size * sizeof(Tdata_CPU));
	}

	static void copy_row(Tdata_GPU *target, const Tdata_CPU *source,
	                     const std::size_t size, std::false_type)
	{
		for (std::size_t i = 0; i < size; ++i)
			target[i] = GPU_Backend::data_to_GPU(source[i]);
	}

	static void insert_data_impl(
		std::vector<Tdata_GPU> &h_data,
		const Tensor<Tdata_CPU> &tensor,
		std::true_type)
	{
		h_data.insert(
			h_data.end(),
			tensor.ptr(),
			tensor.ptr() + tensor.shape.get_shape_all());
	}

	static void insert_data_impl(
		std::vector<Tdata_GPU> &h_data,
		const Tensor<Tdata_CPU> &tensor,
		std::false_type)
	{
		const std::size_t size = tensor.shape.get_shape_all();
		h_data.resize(h_data.size() + size);
		const auto ptr_dest = h_data.end() - size;
		const auto ptr_src = tensor.ptr();
		for(std::size_t i=0; i<size; ++i)
			ptr_dest[i] = GPU_Backend::data_to_GPU(ptr_src[i]);
	}

  public:
	std::vector<std::vector<Tdata_GPU>> h_data;		// 存储数据（CPU）
	Tdata_GPU *d_data = nullptr;					// 存储数据（GPU）
	Tdata_GPU **d_array = nullptr;					// 记录每个batch的 d_data 指针（GPU）
	std::vector<Pack> h_array;					// 记录每个batch的Pack
	std::map<TA, std::map<TAC, Pack>> ptrList;	// 记录每个原子对的Pack
	std::vector<bool> tensor_insert;			// 记录是否当前张量需要insert_data
};

}

}

#endif
