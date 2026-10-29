# Krakowski Klub Go

Static site for [krakow.go.art.pl](https://krakow.go.art.pl/). Polish pages live at `/`, English pages at `/en/`. Pushing to `main` builds the site with Hugo and uploads it to the FTP server.

This directory is the Git repository root. GitHub Actions only runs a workflow that lives at the root of the repository.

## Preview

Install [Hugo 0.168.0](https://github.com/gohugoio/hugo/releases/tag/v0.168.0) (the standard build, not extended), then:

```sh
hugo server
```

## Add an article

Create the same file in both languages:

```sh
hugo new content/pl/p/moj-artykul.md
hugo new content/en/p/moj-artykul.md
```

Write the body in Markdown. Raw HTML such as an iframe is allowed. The page is published at `/p/moj-artykul/` and `/en/p/moj-artykul/`.

## Pin an article to the menu

In the article front matter:

```yaml
title: WSPARCIE
menu:
  main:
    weight: 20
```

Lower weight means further left. `START` stays first. `TURNIEJE` / `TOURNAMENTS` is fixed in `hugo.toml`. Leave `menu` out to keep the page off the bar. The English Wsparcie page is an article without a menu entry, which matches the current site.

## Submenu

Uncomment the parent in `hugo.toml` (there is one for each language), then point the article at it:

```yaml
menu:
  main:
    weight: 20
    parent: o-klubie
```

The parent `identifier` has to match `parent`. A parent with no children is not shown.

## Tournaments

`/turnieje/` is not an article. Add a row to `data/tournaments.yaml`:

```yaml
- name: Turniej o Smoczy Kamień 2027
  start: "2027-05-08"
  end: "2027-05-09"
  url: "https://europeangodatabase.eu/EGD/Tournament_Card.php?&key=T000000"
```

An entry whose end date is still today or later is listed under upcoming tournaments. After that date it moves to finished on the next build. `url` is the EGD registration or results link.

To also show it on the homepage until the day after it ends, set `featured_tournament` in `data/club.yaml`. That card is removed in the browser after `end`, without another build.

## Meetings

The regular meeting is `data/club.yaml` under `regular_meeting`:

- `weekday` (`monday` … `sunday`) is the only value the browser needs. The next date, including today when today is that weekday, is calculated in `Europe/Warsaw` when the page opens. Changing the weekday still needs a commit.
- `card_time`, `card_venue`, and `card_title` are the homepage card.
- `time`, `address`, and `map` are the `/wydarzenia/domowka/` page. `page` is that page's path.

A one-time homepage card is an item in `one_time_events`. It stays visible through `end`, then the browser removes it. Put the long text in `content/pl/wydarzenia/` and `content/en/wydarzenia/`. Set `regular: true` on that page only when its date should keep rolling with the club weekday; otherwise set `date`, `time`, `address`, and `map` in the front matter.

## Embed an SGF

Put the file in `static/sgf/` and add this to the article:

```markdown
{{< sgf src="/sgf/example.sgf" >}}
```

The record is shown with [Besogo](https://github.com/yewang/besogo), vendored under `static/vendor/besogo/` (MIT). See `/p/przyklad-sgf/` for a working example.

## Club games

Put `*.sgf` files in `static/club_games/`. Hugo publishes one page per file at `/partie/<filename>/` and `/en/partie/<filename>/`, and lists them on `/partie/` (20 per page, alphabetical by title). The menu entries are PARTIE and GAMES.

The page title is the first `GN[...]` value in the file. If that property is missing or blank, the title is the filename without the extension. The address follows the filename, not the game name. Hugo reads only the first 1 MB of each file when taking the title; the file itself is still served whole from `static/club_games/`.

## Deploy

On every push to `main`, `.github/workflows/deploy.yml` builds the site and uploads `public/` to `/public_html/`. The repository needs the same secrets as the old Django workflow: `FTP_LOCATION`, `FTP_USERNAME`, and `FTP_PASSWORD`.
