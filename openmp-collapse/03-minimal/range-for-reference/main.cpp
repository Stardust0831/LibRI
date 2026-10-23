#include <iostream>
#include <vector>

void fill(const std::vector<int>& k_indices, const std::vector<int>& atoms,
          std::vector<int>& output)
{
#pragma omp parallel for schedule(static) collapse(2)
    for (const int ik : k_indices)
    {
        for (const int atom : atoms)
        {
            output[ik * atoms.size() + atom] = ik * 100 + atom;
        }
    }
}

int main()
{
    const std::vector<int> k_indices{0, 1, 2};
    const std::vector<int> atoms{0, 1, 2, 3};
    std::vector<int> output(k_indices.size() * atoms.size(), -1);
    fill(k_indices, atoms, output);
    for (const int ik : k_indices)
        for (const int atom : atoms)
            if (output[ik * atoms.size() + atom] != ik * 100 + atom)
            {
                std::cerr << "Unexpected value at " << ik << ", " << atom << "\n";
                return 1;
            }
    std::cout << "All 12 loop results are correct.\n";
    return 0;
}
