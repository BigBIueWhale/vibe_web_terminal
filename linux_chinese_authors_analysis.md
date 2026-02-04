# Linux Kernel Chinese Author Contribution Analysis

## Executive Summary

Analysis of the Linux kernel git repository (1,414,232 commits, 31,280 unique authors) reveals significant Chinese developer participation:

| Estimate Level | Authors | % of Total Authors | Commits | % of Total Commits |
|----------------|---------|-------------------|---------|-------------------|
| **Conservative (High Confidence)** | 4,143 | **13.24%** | 114,680 | **8.11%** |
| **Moderate** | 5,077 | **16.23%** | 144,204 | **10.20%** |
| **Inclusive** | 5,154 | **16.48%** | 145,393 | **10.28%** |

## Key Findings

### 1. Chinese Developers Are a Major Contributor Group

- Over **4,100+ developers** with identifiably Chinese names have contributed to the Linux kernel
- Chinese-named authors account for **~13-16% of all kernel contributors**
- They have authored **~8-10% of all commits** (114,000-145,000 commits)

### 2. Chinese Contributors at All Levels

Chinese developers are found across the entire contribution spectrum:
- **Top individual contributors**: Several Chinese developers rank among the most prolific kernel contributors
- **Major subsystem maintainers**: Chinese engineers maintain critical kernel subsystems
- **Companies**: Major Chinese tech companies (Huawei, Alibaba, Tencent, etc.) are significant contributors

### 3. Top 30 Chinese Contributors by Commit Count

| Rank | Name | Commits |
|------|------|---------|
| 1 | Axel Lin | 3,025 |
| 2 | Herbert Xu | 2,587 |
| 3 | Wei Yongjun | 2,226 |
| 4 | Chen-Yu Tsai | 1,397 |
| 5 | Qu Wenruo | 1,302 |
| 6 | Ming Lei | 1,290 |
| 7 | Yinghai Lu | 1,271 |
| 8 | Shawn Guo | 1,150 |
| 9 | Yang Yingliang | 1,009 |
| 10 | Geliang Tang | 916 |
| 11 | Rex Zhu | 837 |
| 12 | Peng Fan | 835 |
| 13 | Anson Huang | 817 |
| 14 | Zhang Rui | 737 |
| 15 | Kan Liang | 725 |
| 16 | Dave Jiang | 723 |
| 17 | Hawking Zhang | 722 |
| 18 | Martin KaFai Lau | 686 |
| 19 | Jisheng Zhang | 668 |
| 20 | Jiang Liu | 662 |
| 21 | Yonghong Song | 647 |
| 22 | Miaohe Lin | 609 |
| 23 | Yan, Zheng | 603 |
| 24 | Huang Rui | 600 |
| 25 | Yang Li | 586 |
| 26 | Lu Baolu | 584 |
| 27 | Lai Jiangshan | 573 |
| 28 | Peter Chen | 566 |
| 29 | Huacai Chen | 555 |
| 30 | Bard Liao | 544 |

## Methodology

### Name Identification Approach

1. **Chinese Character Detection**: Names containing Chinese characters (Unicode CJK range) are definitively identified
2. **Surname Analysis**: Common Chinese surnames in pinyin (Zhang, Wang, Li, Liu, Chen, etc.) and alternative romanizations (Cantonese, Wade-Giles)
3. **Name Pattern Matching**: Recognition of both Chinese naming conventions (surname-first) and Western-adapted formats (surname-last)
4. **Confidence Levels**:
   - **Definite**: Contains Chinese characters
   - **High**: High-confidence Chinese surname with Chinese-looking or Western given name
   - **Medium**: Medium-confidence surname patterns
   - **Low**: Ambiguous surnames requiring Chinese-looking given names

### Limitations

- Some Chinese developers may use completely Western names (not counted)
- Some non-Chinese people may have Chinese-sounding names (potential overcounting)
- Ethnic Chinese from Taiwan, Singapore, Malaysia, etc. are included in "Chinese" (broader definition)

## Implications

### "Secure by Avoiding Chinese Software" Is a Myth

This analysis demonstrates that:

1. **Linux is international** - developers from China, USA, Europe, Asia, and worldwide contribute
2. **Chinese code is already everywhere** - any system running Linux contains code written by Chinese developers
3. **Open source transcends borders** - the security model of open source is transparency and review, not geography
4. **Major companies depend on Chinese contributions** - Google, Microsoft, Amazon, Meta all use Linux with Chinese contributions

### The Reality of Global Software Development

- Every major operating system has international contributors
- Security comes from code review, not developer nationality
- Attempting to avoid all Chinese-contributed software is practically impossible
- The Linux kernel is literally built by the world, including substantial Chinese participation

## Raw Data Files

- `/tmp/chinese_authors_detailed_v2.txt` - Full list of identified Chinese authors
- `/tmp/linux_authors_unique.txt` - All unique author names
- `/tmp/linux_authors.txt` - Authors with commit counts

---

*Analysis performed on Linux kernel repository (torvalds/linux) on 2026-02-04*
*Total commits analyzed: 1,414,232*
*Total unique authors: 31,280*
