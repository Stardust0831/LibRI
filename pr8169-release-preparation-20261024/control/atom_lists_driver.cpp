#include "unittests/ri/LRI-k-atom-lists-test.hpp"

int main(int argc, char **argv)
{
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &provided);
    int result = 0;
    try
    {
        const std::string suite = argc > 1 ? argv[1] : "all";
        if (suite != "cvc") LRI_K_Atom_Lists_Test::test_hartree();
        if (suite != "hartree") LRI_K_Atom_Lists_Test::test_cvc();
    }
    catch (const std::exception &error)
    {
        std::cerr << error.what() << std::endl;
        result = 1;
    }
    MPI_Finalize();
    return result;
}
