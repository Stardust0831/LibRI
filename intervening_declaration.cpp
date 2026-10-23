#include <vector>
void probe(const std::vector<int>& k_indices, const std::vector<int>& list_IJ, int* out) {
#pragma omp parallel for schedule(static) collapse(2)
    for (int ik_index = 0; ik_index < k_indices.size(); ++ik_index) {
        const int ik = k_indices[ik_index];
        for (int iat1_index = 0; iat1_index < list_IJ.size(); ++iat1_index) {
            const int iat1 = list_IJ[iat1_index];
            out[ik * 16 + iat1] = ik + iat1;
        }
    }
}
