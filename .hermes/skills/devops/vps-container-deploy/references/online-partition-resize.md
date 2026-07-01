# Online partition resize on Linux

When a fresh VPS has a tiny disk (we saw 3.5GB total — way too small for Docker), you can't reinstall, but you can usually grow the disk in the provider's panel and resize the partition + filesystem online, no reboot, no data loss.

This is the procedure we used to grow `/dev/sda1` on Ubuntu 24.04 from 2.5GB to 75GB after the provider allocated 80GB to the underlying virtual disk.

## Detect the situation

```bash
# Underlying disk — what the provider sees
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT

# What Linux is using — what's actually mounted
df -h / | tail -1
```

If `lsblk` shows the disk is larger than `df` reports, the OS doesn't know yet. Example from our session:

```
NAME     SIZE FSTYPE   MOUNTPOINT
sda      80.5G
├─sda1   2.5G ext4    /        ← still 2.5GB, partition table hasn't grown
```

## One-shot fix (no reboot, ~3 seconds)

```bash
# Install growpart if not already present (cloud-images usually have it via cloud-guest-utils)
which growpart || apt-get install -y cloud-guest-utils

# Grow partition 1 on /dev/sda to fill all available space
growpart /dev/sda 1
# Example output: CHANGED: partition=1 start=2099200 old: size=5240799 new: size=166721503

# Now tell ext4 to use all the new space
resize2fs /dev/sda 1
# Example: The filesystem on /dev/sda1 is now 20840187 (4k) blocks long.

# Verify
df -h /
```

That's it. No unmount, no reboot. Filesystem is mounted the whole time.

## What growpart actually does

`growpart` reads the current partition table, calculates free space after the last partition, and rewrites the partition entry to extend into that space. It's safe — it refuses to shrink, and refuses to operate if it can't determine the existing layout.

For ext4 filesystems, `resize2fs` grows online (mountpoint stays live). XFS requires `xfs_growfs` instead, and that command REQUIRES the filesystem to be mounted (it uses the mountpoint, not the device).

## Edge cases

| Situation | Fix |
|---|---|
| Disk was just added, no partition table change | Use `growpart` — it will detect the new space |
| Disk was resized but no partitions exist on the new space | Need to create a partition first with `fdisk`/`parted`, then format |
| Partition is on a non-`/dev/sdX` device (NVMe: `/dev/nvme0n1p1`) | `growpart /dev/nvme0n1 1` — same syntax, different device |
| Underlying disk grew but `df` shows old size | Forgot to run `resize2fs` — partition grew but filesystem didn't |
| Underlying disk grew but `lsblk` shows old partition size | Forgot to run `growpart` — disk grew, partition didn't |

## Don't do this for the boot partition

If `/boot` is its own partition (Ubuntu often has `/boot` at ~1GB), it's small for a reason — usually doesn't need to grow. Touching it risks breaking the bootloader. Leave `/boot` alone, focus on `/`.

## When this DOESN'T work

- **BIOS / legacy boot disks** with MBR partition table — MBR caps at 2TB per disk. Use GPT instead, or accept the limit.
- **LVM volumes** — `growpart` operates on physical volumes; you'll also need `lvextend` + `resize2fs` on the LV.
- **LUKS-encrypted root** — extra `cryptsetup resize` step needed.

## What we observed on our 3.5GB → 75GB grow

```bash
$ lsblk -o NAME,SIZE /dev/sda1
NAME   SIZE
sda1   79.5G                          # after growpart

$ df -h / | tail -1
/dev/sda1   77G  2.3G  75G  3% /     # after resize2fs
```

Total wall time: 3 seconds. Container runtime fully available throughout.