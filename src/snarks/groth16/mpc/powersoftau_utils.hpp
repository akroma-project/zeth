// Copyright (c) 2015-2019 Clearmatics Technologies Ltd
//
// SPDX-License-Identifier: LGPL-3.0+

#ifndef __ZETH_SNARKS_GROTH_POWERSOFTAU_UTILS_HPP__
#define __ZETH_SNARKS_GROTH_POWERSOFTAU_UTILS_HPP__

#include "include_libsnark.hpp"

#include <istream>

namespace libzeth
{

/// Output from the first phase of the MPC (powersoftau). The structure
/// matches that data exactly (no indication of degree, etc), so that it can be
/// loaded directly. Implements the interface of StructuredT.
template<typename ppT> class srs_powersoftau
{
public:
    /// { [ x^i ]_1 }  i = 0 .. 2n-2
    const libff::G1_vector<ppT> tau_powers_g1;

    /// { [ x^i ]_2 }  i = 0 .. n-1
    const libff::G2_vector<ppT> tau_powers_g2;

    /// { [ alpha . x^i ]_1 }  i = 0 .. n-1
    const libff::G1_vector<ppT> alpha_tau_powers_g1;

    /// { [ beta . x^i ]_1 }  i = 0 .. n-1
    const libff::G1_vector<ppT> beta_tau_powers_g1;

    /// [ beta ]_2
    const libff::G2<ppT> beta_g2;

    srs_powersoftau(
        libff::G1_vector<ppT> &&tau_powers_g1,
        libff::G2_vector<ppT> &&tau_powers_g2,
        libff::G1_vector<ppT> &&alpha_tau_powers_g1,
        libff::G1_vector<ppT> &&beta_tau_g1,
        const libff::G2<ppT> &beta_g2);

    bool is_well_formed() const;
};

/// Encodings of lagrange polynomials at tau, computed from
/// powersoftau, on some domain of degree n.
template<typename ppT> class srs_lagrange_evaluations
{
public:
    const size_t degree;

    /// ${ [ L_i(x) ]_1 }_i$
    std::vector<libff::G1<ppT>> lagrange_g1;

    /// ${ [ L_i(x) ]_2 }_i$
    std::vector<libff::G2<ppT>> lagrange_g2;

    /// ${ [ alpha . L_i(x) ]_1 }"$
    std::vector<libff::G1<ppT>> alpha_lagrange_g1;

    /// ${ [ beta . L_i(x) ]_1 }"$
    std::vector<libff::G1<ppT>> beta_lagrange_g1;

    srs_lagrange_evaluations(
        size_t degree,
        std::vector<libff::G1<ppT>> &&lagrange_g1,
        std::vector<libff::G2<ppT>> &&lagrange_g2,
        std::vector<libff::G1<ppT>> &&alpha_lagrange_g1,
        std::vector<libff::G1<ppT>> &&beta_lagrange_g1);

    bool is_well_formed() const;
    void write(std::ostream &out) const;
    static srs_lagrange_evaluations read(std::istream &in);
};

/// Given some secrets, compute a dummy set of powersoftau, for
/// circuits with polynomials A, B, C order-bound by `n` .
template<typename ppT>
srs_powersoftau<ppT> dummy_powersoftau_from_secrets(
    const libff::Fr<ppT> &tau,
    const libff::Fr<ppT> &alpha,
    const libff::Fr<ppT> &beta,
    size_t n);

/// Same as dummy_powersoftau_from_secrets(), where the secrets are not of
/// interest.
template<typename ppT> srs_powersoftau<ppT> dummy_powersoftau(size_t n);

// Utility functions for reading and writing data as formatted by the
// powersoftau process.

void read_powersoftau_fr(std::istream &in, libff::alt_bn128_Fr &fr_out);
void read_powersoftau_fq2(std::istream &in, libff::alt_bn128_Fq2 &fq2_out);
void read_powersoftau_g1(std::istream &in, libff::alt_bn128_G1 &out);
void read_powersoftau_g2(std::istream &in, libff::alt_bn128_G2 &out);

void write_powersoftau_fr(std::ostream &out, const libff::alt_bn128_Fr &fr);
void write_powersoftau_fq2(std::ostream &out, const libff::alt_bn128_Fq2 &fq2);
void write_powersoftau_g1(std::ostream &out, const libff::alt_bn128_G1 &g1);
void write_powersoftau_g2(std::ostream &out, const libff::alt_bn128_G2 &g2);

/// Load data generated by zcash's powersoftau tools (modified to use
/// the bn library):
///   https://github.com/clearmatics/powersoftau
///
/// Expect at least 'n' powers in the file.
srs_powersoftau<libff::alt_bn128_pp> powersoftau_load(
    std::istream &in, size_t n);

/// Write powersoftau data, in the format compatible with
/// powersoftau_load.
void powersoftau_write(
    std::ostream &in, const srs_powersoftau<libff::alt_bn128_pp> &pot);

/// Implements the SameRatio described in "Scalable Multi-party Computation for
/// zk-SNARK Parameters in the Random Beacon Model"
/// http://eprint.iacr.org/2017/1050
template<typename ppT>
bool same_ratio(
    const libff::G1<ppT> &a1,
    const libff::G1<ppT> &b1,
    const libff::G2<ppT> &a2,
    const libff::G2<ppT> &b2);

/// Given two sequences a1s and b1s, check (with high probability) that
///   same_ratio((a1s[i], b1s[i]), (a2, b2))
/// holds for all i. For random field values r_i, sum up:
///   a1 = a1s[0] * r_0 + ... + a1s[n] * r_n
///   b1 = b1s[0] * r_0 + ... + b1s[n] * r_n
/// and check same_ratio((a1, b1), (a2, b2)).
///
/// (Based on merge_pairs function from https://github.com/ebfull/powersoftau/)
template<typename ppT>
bool same_ratio_vectors(
    const std::vector<libff::G1<ppT>> &a1s,
    const std::vector<libff::G1<ppT>> &b1s,
    const libff::G2<ppT> &a2,
    const libff::G2<ppT> &b2);

/// same_ratio_vectors implementation for vectors of G2 elements.
template<typename ppT>
bool same_ratio_vectors(
    const libff::G1<ppT> &a1,
    const libff::G1<ppT> &b1,
    const std::vector<libff::G2<ppT>> &a2s,
    const std::vector<libff::G2<ppT>> &b2s);

/// Checks that consecutive entries in a1s all have a ratio consistent with (a2,
/// b2).
template<typename ppT>
bool same_ratio_consecutive(
    const std::vector<libff::G1<ppT>> &a1s,
    const libff::G2<ppT> &a2,
    const libff::G2<ppT> &b2);

/// same_ratio_consecutive implementation for vectors of G2 elements.
template<typename ppT>
bool same_ratio_consecutive(
    const libff::G1<ppT> &a1,
    const libff::G1<ppT> &b1,
    const std::vector<libff::G2<ppT>> &a2s);

/// Verify that the pot data is well formed.
template<typename ppT>
bool powersoftau_is_well_formed(const srs_powersoftau<ppT> &pot);

/// Compute the evaluation of the lagrange polynomials in G1 and G2, along with
/// some useful factors. The results can be cached and used against any QAP,
/// provided its domain size matched.
template<typename ppT>
srs_lagrange_evaluations<ppT> powersoftau_compute_lagrange_evaluations(
    const srs_powersoftau<ppT> &pot, const size_t n);

} // namespace libzeth

#include "snarks/groth16/mpc/powersoftau_utils.tcc"

#endif // __ZETH_SNARKS_GROTH_POWERSOFTAU_UTILS_HPP__
