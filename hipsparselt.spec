# Structured-sparsity BLAS. TheRock 10.0.

Name:		hipsparselt
Version:	10.0.0
Release:	1
Summary:	HIP structured-sparsity sparse-matrix library
License:	MIT
Group:		System/Libraries
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.0/hipsparselt.tar.gz#/hipsparselt-%{version}.tar.gz
# TheRock hipSPARSELt add_subdirectory()s a sibling hipblaslt tree for tensilelite-host.
Source1:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.0/hipblaslt.tar.gz#/hipblaslt-%{version}.tar.gz
# Same origami/system-rocisa fix as hipblaslt; applied to Source1 after unpack
Source2:	hipblaslt-0002-system-deps-find-package.patch
# Host memcpy/strcpy vs hip device memcpy when compiled -x hip
Patch0:		0001-include-cstring-for-memcpy-strcpy.patch

BuildRequires:	rocm-rpm-macros
BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	rocm-cmake
BuildRequires:	hipcc
BuildRequires:	rocm-hip-devel
BuildRequires:	hipsparse-devel
BuildRequires:	hipblas-common-devel
BuildRequires:	cmake(hipblaslt)
BuildRequires:	cmake(amd_smi)
BuildRequires:	cmake(origami)
BuildRequires:	cmake(msgpack-cxx)
BuildRequires:	boost-devel
BuildRequires:	pkgconfig(python)
BuildRequires:	python%{pyver}dist(rocisa)
BuildRequires:	python%{pyver}dist(pyyaml)
BuildRequires:	openmp-devel
BuildRequires:	cmake(AMDDeviceLibs)
BuildRequires:	clang >= %{rocm_llvm_maj_ver}

%description
hipSPARSELt implements structured-sparsity GEMM (the HIP counterpart
of cuSPARSELt). PyTorch USE_HIPSPARSELT needs this library.

%package devel
Summary:	Development files for %{name}
Group:		Development/C++
Requires:	%{name}%{?_isa} = %{version}-%{release}
Requires:	hipsparse-devel

%description devel
Headers and CMake package for hipSPARSELt.

%prep
%autosetup -n hipsparselt -p1
cd ..
tar xf %{SOURCE1}
# Prefer installed origami; do not add_subdirectory ../../shared/origami
patch -p1 --fuzz=0 -d hipblaslt < %{SOURCE2}
cd hipsparselt

%build
# hipcc as CXX compiles host .cpp with -x hip; hip's __device__ memcpy
# then shadows libc. Same as hipblaslt: clang++ for host, clang++ for HIP.
export CXX=clang++
export CC=clang
export ROCM_PATH=%{_prefix}
export HIP_PATH=%{_prefix}
export HIP_DEVICE_LIB_PATH=%{_libdir}/amdgcn/bitcode
export CMAKE_HIP_FLAGS="%{rocm_hip_clang_flags}"
export TMPDIR=%{_builddir}/.hsplt-tmp
mkdir -p "$TMPDIR"
CXXFLAGS=$(printf '%s' "%{optflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CXXFLAGS
%cmake %{rocm_cmake_fhs} \
	-DAMDGPU_TARGETS="gfx942;gfx950" \
	-DGPU_TARGETS="gfx942;gfx950" \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_CXX_COMPILER=clang++ \
	-DCMAKE_HIP_COMPILER=clang++ \
	-DCMAKE_HIP_FLAGS="%{rocm_hip_clang_flags}" \
	-DCMAKE_CXX_FLAGS="$CXXFLAGS --rocm-path=%{_prefix} --rocm-device-lib-path=%{_libdir}/amdgcn/bitcode" \
	-DOpenMP_CXX_FLAGS=-fopenmp \
	-DOpenMP_CXX_LIB_NAMES=omp \
	-DOpenMP_omp_LIBRARY=%{_libdir}/libomp.so \
	-DHIPSPARSELT_BUILD_TESTING=OFF \
	-DHIPSPARSELT_ENABLE_CLIENT=OFF \
	-DHIPSPARSELT_ENABLE_BENCHMARKS=OFF \
	-DHIPSPARSELT_ENABLE_SAMPLES=OFF \
	-DHIPSPARSELT_ENABLE_MARKER=OFF \
	-DHIPSPARSELT_ENABLE_FETCH=OFF \
	-DHIPBLASLT_BUNDLE_PYTHON_DEPS=OFF \
	-DHIPBLASLT_ENABLE_FETCH=OFF \
	-DHIPBLASLT_ENABLE_ROCROLLER=OFF \
	-DHIPSPARSELT_HIPBLASLT_PATH="%{_builddir}/hipblaslt" \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja
%ninja_build

%install
%ninja_install -C build

%files
%license LICENSE.md
%doc README.md
%{_libdir}/libhipsparselt.so.*

%files devel
%{_includedir}/hipsparselt/
%{_libdir}/libhipsparselt.so
%{_libdir}/cmake/hipsparselt/
