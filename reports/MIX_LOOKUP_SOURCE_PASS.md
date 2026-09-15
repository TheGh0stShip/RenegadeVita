# MIX lookup source pass

Status: source inspection and registered loader hardening; unbuilt, untested.
No retail mutation, archive extraction, new runtime index or device access.

Additional source ownership fix: return the constructor's non-null file object
when Is_Available fails, and return Build_Filename_List's file object whether
Open succeeds or fails. Both use the original supplying factory; successful
paths still return once. Registered wwlib-a35-mix-failure-file-release.patch.
This removes unbalanced failure-path ownership, not source data or diagnostics.
Actual repeated-load memory improvement remains unmeasured under the test hold.

Original MixFileFactoryClass::Get_File already binary-searches its resident
CRC index. Directory enumeration serves original menus; it is not a demonstrated
per-frame asset bottleneck. The generated filename-cache health helper does not
replace actual asset lookup. Do not claim filename-cache validation accelerates
MIX reads, or add a second archive index without a demonstrated need.

Constructor inspection found signed header offsets and FileCount used for seek,
allocation and count-times-entry-size without checking them against archive size.
The new wwlib-a35-mix-index-allocation-bounds.patch checks offsets before seeking
and derives the maximum count from actual remaining index bytes before allocating.
This avoids negative/overflowing count-derived sizes and skips indexing element
zero for an empty table. It uses no arbitrary retail-file-count limit and keeps
the original binary search, archive owner, CRC semantics and asset format.

This is robustness work discovered during the optimization pass, not an FPS gain
or evidence identifying the cause of previous Vita3K crashes. It does not claim
complete malformed-archive hardening: allocation failure, filename-table contents
and individual entry ranges remain separate contracts. Later validation must
include unchanged current retail, empty indexes, truncated headers/counts and
negative or out-of-file offsets. No validation was run during the current hold.
