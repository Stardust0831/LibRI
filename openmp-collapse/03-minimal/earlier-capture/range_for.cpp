#include <vector>
void probe(const std::vector<int>& k_indices, const std::vector<int>& list_IJ, int* out) {
#pragma omp parallel for schedule(static) collapse(2)
    for (const int ik : k_indices) {
        for (const int iat1 : list_IJ) {
            out[ik * 16 + iat1] = ik + iat1;
        }
    }
}
