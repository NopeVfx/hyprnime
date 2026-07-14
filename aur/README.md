# Publishing Hyprnime to the AUR

Two package variants are here, for two different stages of the project:

- **`hyprnime-git/`** -- builds from the latest commit on your GitHub repo's
  `main` branch. No release tag needed. **Submit this one first** -- it's
  the fastest path to actually being on the AUR today.
- **`hyprnime/`** -- builds from a tagged GitHub release (currently pinned
  to `v0.1.0`). Use this once you've actually cut that release; until then
  it will fail to build because the tag doesn't exist yet.

I can't do the actual submission for you (no AUR account or SSH key of
mine involved here), but everything below is copy-pasteable.

## 0. Prerequisites

1. **Push the project to GitHub first** (see the main README's "Publishing
   this to GitHub" section) -- both PKGBUILDs point at
   `https://github.com/NopeVfx/hyprnime`, so replace `NopeVfx`
   in both `PKGBUILD` files (and the `url=` field) with your actual GitHub
   username before doing anything else.
2. **Create an AUR account**: https://aur.archlinux.org/register
3. **Add an SSH key** to that account (Account → My Account → SSH
   Public Key). If you don't have one yet: `ssh-keygen -t ed25519`, then
   paste the contents of `~/.ssh/id_ed25519.pub`.
4. **Test the SSH connection**: `ssh aur@aur.archlinux.org help` should
   print AUR's help text, not an auth error.

## 1. Test-build it locally first

Do this before publishing anything -- it's the single best way to catch a
packaging mistake before it's public:

```bash
cd aur/hyprnime-git
makepkg -si
```

`-s` pulls in build/runtime deps automatically, `-i` installs the result
straight away so you can actually launch `hyprnime` afterward and confirm
it works. If it builds and runs, you're good.

## 2. Regenerate .SRCINFO with the real tool

I hand-wrote the `.SRCINFO` files in this repo in the standard format
since I don't have `makepkg` available to generate them myself -- treat
them as a starting point, not gospel. Regenerate the real one before you
push, from inside each package's folder:

```bash
cd aur/hyprnime-git
makepkg --printsrcinfo > .SRCINFO
```

AUR rejects pushes where `.SRCINFO` doesn't match `PKGBUILD`, so this step
isn't optional.

## 3. Push hyprnime-git to the AUR

Each AUR package is its own tiny git repo, separate from your project
repo. First push creates it:

```bash
cd aur/hyprnime-git
git init
git remote add origin ssh://aur@aur.archlinux.org/hyprnime-git.git
git add PKGBUILD .SRCINFO
git commit -m "Initial import: hyprnime-git 0.1"
git push -u origin master
```

It should now be live at `https://aur.archlinux.org/packages/hyprnime-git`.

## 4. Later: publish the tagged hyprnime package too

Once you've cut an actual `v0.1.0` tag/release on GitHub:

```bash
cd aur/hyprnime
# replace the SKIP checksum with a real one:
curl -sL "https://github.com/NopeVfx/hyprnime/archive/refs/tags/v0.1.0.tar.gz" | sha256sum
# paste that hash into sha256sums=() in PKGBUILD, replacing 'SKIP'
makepkg --printsrcinfo > .SRCINFO
makepkg -si   # test-build locally first, same as above

git init
git remote add origin ssh://aur@aur.archlinux.org/hyprnime.git
git add PKGBUILD .SRCINFO
git commit -m "Initial import: hyprnime 0.1.0"
git push -u origin master
```

`pacman-contrib` has an `updpkgsums` tool that does the checksum step
automatically if you'd rather not pipe curl into sha256sum by hand.

## Notes / things worth knowing

- **Keep both variants' `pkgver`/`pkgrel` and dependency lists in sync**
  when you change one -- they'll drift apart otherwise (this is a general
  AUR footgun with `-git` + release package pairs, not specific to this
  project).
- **`sha256sums=('SKIP')` on `hyprnime-git`** is normal and expected for
  VCS sources (git clones are already content-addressed by commit, a
  separate checksum doesn't add anything) -- only the tagged `hyprnime`
  package's tarball checksum should ever be a real hash, not `SKIP`.
- If `namcap` is installed (`sudo pacman -S namcap`), running
  `namcap PKGBUILD` and `namcap *.pkg.tar.zst` after a build is the
  standard sanity check AUR maintainers use before publishing -- worth
  doing once before your first push.
- After publishing, AUR shows a "Maintainer" field pulled from the
  `# Maintainer:` comment at the top of each PKGBUILD -- update the
  placeholder email in both files to yours.
