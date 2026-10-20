# Structured-sparsity BLAS. TheRock 10.1.

# Helper .hsaco are AMDGPU ELF ET_DYN. Full find-debuginfo strip drops .symtab
# and hipModuleLoad then returns "device kernel image is invalid".
%global _find_debuginfo_opts -g

Name:		hipsparselt
Version:	10.1.0
Release:	1
Summary:	HIP structured-sparsity sparse-matrix library
License:	MIT
Group:		System/Libraries
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.1/hipsparselt.tar.gz#/hipsparselt-%{version}.tar.gz
# TheRock hipSPARSELt add_subdirectory()s a sibling hipblaslt tree for tensilelite-host.
Source1:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.1/hipblaslt.tar.gz#/hipblaslt-%{version}.tar.gz
# Same origami/system-rocisa fix as hipblaslt; applied to Source1 after unpack
Source2:	hipblaslt-0002-system-deps-find-package.patch
# Skip TensileLogic --check-all (OOMs); one TensileCreateLibrary per gfx*
Source3:	hipblaslt-0005-per-arch-tensile-create-library.patch
# writeSolutionsAndKernelsTCL kept every kernel's assembly text. gfx942
# (51431 kernels) is SIGKILL'd at ~5% even in-process. Return occupancy only.
Source4:	hipblaslt-0006-drop-asm-text.patch
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
BuildRequires:	python%{pyver}dist(joblib)
BuildRequires:	python%{pyver}dist(msgpack)
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
patch -p1 --fuzz=0 -d hipblaslt < %{SOURCE3}
patch -p1 --fuzz=0 -d hipblaslt < %{SOURCE4}
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
# Tensile defaults to one worker per CPU. gfx942 logic is 1.3 GiB of YAML
# (162 files, 88327 solutions). Forking workers after that load is SIGKILL'd
# (8 and 2 workers). One in-process worker still died at 5% of 51431 kernels
# because the result list kept every assembly text. Source4 drops that text.
# Stay at 1 worker: a fork would copy the loaded solution set again.
%global tensile_jobs 1
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
	-DTENSILELITE_BUILD_PARALLEL_LEVEL=%{tensile_jobs} \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja
RPM_BUILD_NCPUS=%{tensile_jobs}
export RPM_BUILD_NCPUS
%ninja_build

%install
%ninja_install -C build
find %{buildroot} -name '*.hsaco' -exec chmod 644 {} +
rm -f %{buildroot}%{_docdir}/hipsparselt/LICENSE.md

%files
%license LICENSE.md
%doc README.md
%{_libdir}/libhipsparselt.so.*
%{_libdir}/hipsparselt/

%files devel
%{_includedir}/hipsparselt/
%{_libdir}/libhipsparselt.so
%{_libdir}/cmake/hipsparselt/
