# Grover 搜索算法详解

## 参数设置

- `n`: 数据寄存器的量子比特数（例如 3 比特对应 $2^3=8$ 个状态）。
- `target`: 要搜索的目标状态的二进制字符串（例如 `'101'`）。

> **总结**：该算法的输入为量子比特数 `n` 和目标态的二进制字符串 `target`。算法采用 Grover 搜索方法：首先构造 `n` 比特均匀叠加初态，根据初始成功概率 $1/2^n$ 自动计算最优迭代次数，然后重复执行 Oracle（标记目标态）和 diffuser（放大目标振幅）组成的 Grover 迭代。最终输出测量概率最高的态（期望即为目标态 `target`）及其概率、计算时间和生成的量子线路图。

---

## 目录

- [运行流程](#运行流程)
- [核心思想](#核心思想)
- [数学原理](#数学原理)
- [算法步骤](#算法步骤)
- [量子优势](#量子优势)
- [复杂度分析](#复杂度分析)
- [应用与影响](#应用与影响)

---

## 运行流程

1. **状态初始化**: 使用 Hadamard 门制备所有基态的均匀叠加态。
2. **Oracle (算子)**: 标记目标状态，通过辅助比特反转目标态的相位。
3. **Diffuser (扩散算子)**: 对所有状态的平均振幅进行反射，从而增加目标态的概率幅。
4. **迭代**: 重复上述 Oracle 和 Diffuser 步骤，次数约为 $\frac{\pi}{4}\sqrt{N}$。
5. **测量**: 测量数据寄存器，以极高概率得到目标状态。

---

## 核心思想

- **相位旋转Oracle（标记好解）**：把好解的相位翻转（乘上-1）。
- **Diffusion（关于平均值反射）**：把所有振幅围绕平均值做一次反射。

---

## 数学原理

设搜索空间是 $\{|x\rangle: x\in\{0,\dots,N-1\}\}$​。定义“好解集合” G，大小 |G|=M。

把态空间分解成两个正交单位向量：$|w\rangle=\frac{1}{\sqrt{M}}\sum_{x\in G}|x\rangle,\ |r\rangle=\frac{1}{\sqrt{N-M}}\sum_{x\notin G}|x\rangle.$

初态取均匀叠加：$|s\rangle=\frac{1}{\sqrt{N}}\sum_{x=0}^{N-1}|x\rangle = \sqrt{\frac{M}{N}}\,|w\rangle+\sqrt{\frac{N-M}{N}}\,|r\rangle.$

令$\sin\theta=\sqrt{\frac{M}{N}},\ \cos\theta=\sqrt{\frac{N-M}{N}}$, 则$|s\rangle=\sin\theta\,|w\rangle+\cos\theta\,|r\rangle$. 

我们首先作用相位旋转Oracle：$O_f|x\rangle = (-1)^{f(x)}|x\rangle$,其中 f(x)=1 表示 x 是好解。于是它对 $|x\rangle, \ x\in G $分量乘 -1，对$ |x\rangle,\ x\notin G$ 不变。

然后我们作用Diffusion态（关于$\ket{s}$反射）：$D = 2|s\rangle\langle s|-I.$

于是我们就有Grover迭代算子：$G=DO_{f}$。事实上，从初态$\ket{s}$ 出发，经过$k$次迭代后可以得到：$G^k|s\rangle = \sin((2k+1)\theta)\,|w\rangle+\cos((2k+1)\theta)\,|r\rangle.$

为了让成功概率接近 1，希望$(2k+1)\theta \approx \frac{\pi}{2}$，所以$k \approx \frac{\pi}{4\theta}-\frac{1}{2}$，当 $M\ll N$ 时，$\theta \approx \sqrt{M/N}$，于是$k = \Theta\!\left(\sqrt{\frac{N}{M}}\right)$.

特别地，若只有一个解 M=1，查询 oracle 的次数是 $\Theta(\sqrt{N})$，这就是 Grover 的平方加速。

当候选解的分布并非均匀分布时，我们假设初态是$\ket{z}$，$|z\rangle=\sin\gamma\,|w\rangle+\cos\gamma\,|r\rangle$，依旧考虑关于$\ket{z}$的反射。则经过$k$次迭代后可以得到：$G^k|z\rangle = \sin((2k+1)\gamma)\,|w\rangle+\cos((2k+1)\gamma)\,|r\rangle.$

**对于相位旋转Oracle**: 我们需如下oracle$U_{f}$满足：$U_{f}\ket{x,y} = \ket{x,y\oplus f(x)}$，$x\in\{0,1\}^{n},\ y\in\{0,1\}$。由这个oracle，配合一个辅助量子比特，我们就能实现前文中提及的$O_{f}$。考虑$\ket{-} = \frac{1}{\sqrt{2}}(\ket{0}-\ket{1})$，那么将$U_{f}$作用到态$\ket{x}\ket{-}$上，我们就实现了$O_{f}$，事实上：
$$
U_f\big(|x\rangle|-\rangle\big)
=(-1)^{f(x)}|x\rangle|-\rangle.
$$
至于$U_{f}$的实现，难度主要在于构造一个可逆的电路去计算$f(x)$。

**对于Diffusion**：我们假设已经有了制备$\ket{z}$的oracle$U_{z}$，那么我们有如下推导：
$$
D= 2\ket{z}\bra{z}-I = U_{z}(2\ket{0}\bra{0}-I)U_{z}^{\dagger}
$$
这样我们就可以实现Grover算法。

---

## 算法步骤

1. **制备初始态**：使用 Hadamard 门将数据寄存器初始化为所有可能状态的均匀叠加态。
2. **应用 Oracle**：对处于目标状态的波函数执行倒相操作（相位子翻转乘上 -1）。
3. **应用 Diffusion**：对所有的概率振幅关于平均值执行反演操作，将偏极放大。
4. **循环执行**：结合 2、3 步骤组成单轮搜索探测，直到 $k \approx \frac{\pi}{4\theta}$。
5. **观测投影**：收集数据寄存器的最终波幅呈现出的峰值形态。

---

## 量子优势

| 任务 | 经典穷举 | 量子 Grover |
|------|-----------|----------------|
| 无序列表反向寻找 | $O(N)$ | $O(\sqrt{N})$ |

---

## 复杂度分析

Grover 搜索将无结构的数据检索复杂度从经典所需的 $O(N)$ 降维打击到了 $O(\sqrt{N})$。然而如果不节制地施加计算循环迭代过度，反而会因为周期性使概率峰值偏离回去。因此停止点的约束是使用该算法的最核心技术门槛之一。

---

## 应用与影响

### 振幅放大（Amplitude Amplification）

考虑如下在量子算法中经常出现的情景：考虑一个目标态$\ket{\psi_{0}}$的制备需要$m$个辅助量子比特，也就是说：
$$
U_{\psi_{0}}\ket{0}^{m}\ket{0}^{n} = \sqrt{p_{0}}\ket{0}^{m}\ket{\psi_{0}} + \sqrt{1-p_{0}}\ket{\perp}
$$
我们的目标是通过上述的Grover迭代过程将获得目标态的概率$p_{0}$放大。首先考虑相位旋转oracle：

考虑$O_{f} = (I^{\otimes m} - 2\ket{0}^{m}\bra{0}^{m})\otimes I^{\otimes n}$，那么$O_{f}$就可以将前m个qubit都为零的态的相位乘上$-1$。事实上，我们可以实现$O_{f}$使得相位乘上$e^{i\phi}$。其具体实现和QSP中的$CRZ$完全一致。

然后考虑Diffusion $D$，由前方讨论易知，$D = U_{\psi_{0}}(2\ket{0^{m+n}}\bra{0^{m+n}}-I)U_{\psi_{0}}^{\dagger}$

令$G = DO_{f}$，迭代$k = O(\frac{1}{\sqrt{p_{0}}})$次，我们就能以$\Omega(1)$的重复次数获得目标态$\ket{\psi_{0}}$。
