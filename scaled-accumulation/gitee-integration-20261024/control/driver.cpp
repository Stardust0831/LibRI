#include "unittests/ri/LRI-loop3-test.hpp"

int main(int argc, char **argv)
{
#ifdef TEST_COMPLEX
    using Scalar = std::complex<TEST_REAL>;
#else
    using Scalar = TEST_REAL;
#endif
    try
    {
        LRI_Loop3_Test::main<Scalar>(argc, argv);
        return 0;
    }
    catch(const std::exception &error)
    {
        std::cerr << error.what() << std::endl;
        int initialized = 0, finalized = 0;
        MPI_Initialized(&initialized);
        MPI_Finalized(&finalized);
        if(initialized && !finalized)
            MPI_Finalize();
        return 1;
    }
}
