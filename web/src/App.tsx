import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, imageBase64, MAX_IMAGE_BYTES } from "./api";
import type { Match, Person, SearchResponse } from "./api";
import { Icon } from "./Icon";
import { useLocale } from "./i18n";
import { MetadataFields, emptyFields } from "./MetadataFields";
import { Dialog } from "./Dialog";

type Page = "search" | "register" | "library";

export default function App() {
  const { locale, setLocale, t } = useLocale();
  const [page, setPage] = useState<Page>("search");
  const [domain, setDomain] = useState<"people" | "animals">("people");
  const [token, setToken] = useState(
    () => sessionStorage.getItem("heyface.token") ?? "",
  );
  const [tokenDraft, setTokenDraft] = useState("");
  const [showAccess, setShowAccess] = useState(false);
  const [ready, setReady] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [fields, setFields] = useState(emptyFields);
  const [method, setMethod] = useState("facenet");
  const [species, setSpecies] = useState("cat");
  const [consent, setConsent] = useState(false);
  const [cropConfirmed, setCropConfirmed] = useState(false);
  const [exact, setExact] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [records, setRecords] = useState<Person[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [detail, setDetail] = useState<Match | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const accessInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch("/api/v1/health/live")
      .then((r) => setReady(r.ok))
      .catch(() => setReady(false));
  }, []);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (showAccess) accessInput.current?.focus();
  }, [showAccess]);

  function changeDomain(value: "people" | "animals") {
    if (busy) return;
    setDomain(value);
    setMethod(value === "people" ? "facenet" : "dinov2");
    setFile(null);
    setResult(null);
    setError("");
    setNotice("");
    if (value === "animals" && page === "library") setPage("search");
  }
  function chooseFile(candidate?: File) {
    if (!candidate || busy) return;
    if (
      !["image/jpeg", "image/png"].includes(candidate.type) ||
      candidate.size > MAX_IMAGE_BYTES
    ) {
      setError(t("badFile"));
      return;
    }
    setFile(candidate);
    setResult(null);
    setError("");
    setNotice("");
  }
  async function sample() {
    const path =
      domain === "people" ? "/brand/heyface.png" : "/brand/animal.png";
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error(t("genericError"));
      chooseFile(
        new File([await response.blob()], "example.png", { type: "image/png" }),
      );
    } catch {
      setError(t("genericError"));
    }
  }
  function requireAccess() {
    if (token) return true;
    setShowAccess(true);
    return false;
  }
  async function connect(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("methods", tokenDraft.trim(), locale);
      setToken(tokenDraft.trim());
      sessionStorage.setItem("heyface.token", tokenDraft.trim());
      setShowAccess(false);
      setTokenDraft("");
    } catch (e) {
      setError(e instanceof Error ? e.message : t("genericError"));
    } finally {
      setBusy(false);
    }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!requireAccess()) return;
    if (!file) {
      setError(t("missingImage"));
      return;
    }
    if (domain === "animals" && !cropConfirmed) {
      setError(t("cropRequired"));
      return;
    }
    if (page === "register" && !consent) {
      setError(t("authorization"));
      return;
    }
    setBusy(true);
    try {
      const image = await imageBase64(file);
      if (page === "register") {
        const body =
          domain === "people"
            ? {
                image_base64: image,
                person_id: crypto.randomUUID(),
                person: {
                  ...fields,
                  sex: fields.sex || "unspecified",
                  consent,
                },
              }
            : {
                image_base64: image,
                animal_id: crypto.randomUUID(),
                animal: { name: fields.name, species, consent },
                single_subject_confirmed: true,
              };
        await api(domain, token, locale, body);
        setNotice(t("saved"));
        setResult(null);
      } else {
        const filters = Object.fromEntries(
          Object.entries(fields).filter(([, value]) => value),
        );
        const body =
          domain === "people"
            ? { image_base64: image, filters, method, exact, limit: 10 }
            : {
                image_base64: image,
                species,
                method,
                exact,
                limit: 10,
                single_subject_confirmed: true,
              };
        setResult(
          await api<SearchResponse>(
            domain === "people" ? "search" : "animals/search",
            token,
            locale,
            body,
          ),
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("genericError"));
    } finally {
      setBusy(false);
    }
  }
  async function loadRecords(append = false) {
    if (!requireAccess()) return;
    setBusy(true);
    setError("");
    try {
      const query = new URLSearchParams(
        Object.fromEntries(Object.entries(fields).filter(([, value]) => value)),
      );
      if (append && cursor) query.set("cursor", cursor);
      const data = await api<{ items: Person[]; next_cursor: string | null }>(
        "people?" + query,
        token,
        locale,
      );
      setRecords(append ? [...records, ...data.items] : data.items);
      setCursor(data.next_cursor);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("genericError"));
    } finally {
      setBusy(false);
    }
  }
  async function removeRecord() {
    if (!detail || !window.confirm(t("confirmDelete"))) return;
    const entity = detail.person ?? detail.animal;
    try {
      await api(
        `${detail.person ? "people" : "animals"}/${entity!.id}`,
        token,
        locale,
        undefined,
        "DELETE",
      );
      setDetail(null);
      setResult(null);
      setRecords(records.filter((record) => record.id !== entity!.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("genericError"));
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          href="#"
          className="brand"
          aria-label="Heyface"
          onClick={(e) => {
            e.preventDefault();
            if (busy) return;
            setPage("search");
          }}
        >
          <span className="brand-mark">
            h<span>:</span>
          </span>
          heyface<span className="brand-dot">.</span>
        </a>
        <p className="workspace-label">{t("workspace")}</p>
        <nav aria-label={t("workspace")}>
          {(["search", "register", "library"] as const).map((item) => (
            <button
              key={item}
              aria-label={t(item)}
              title={t(item)}
              disabled={busy}
              className={page === item ? "nav-item active" : "nav-item"}
              onClick={() => {
                setPage(item);
                setError("");
                setNotice("");
                if (item === "library") {
                  setDomain("people");
                  void loadRecords();
                }
              }}
            >
              <Icon
                name={
                  item === "search"
                    ? "search"
                    : item === "register"
                      ? "plus"
                      : "grid"
                }
              />
              <span>{t(item)}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <Icon name="shield" size={23} />
          <p>{t("privacy")}</p>
          <span>heyface / 0.1</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="environment">
            <span className={ready ? "status-dot" : "status-dot waiting"} />
            {t("local")}
            <span className="status-copy">
              {t(ready ? "ready" : "offline")}
            </span>
          </div>
          <div className="topbar-actions">
            <select
              aria-label="Language / Idioma"
              value={locale}
              onChange={(e) => setLocale(e.target.value as "en" | "pt-BR")}
            >
              <option value="pt-BR">PT</option>
              <option value="en">EN</option>
            </select>
            <button
              className="access-button"
              disabled={busy}
              onClick={() =>
                token
                  ? (sessionStorage.removeItem("heyface.token"),
                    setToken(""),
                    setResult(null),
                    setRecords([]),
                    setDetail(null),
                    setCursor(null))
                  : setShowAccess(true)
              }
            >
              <Icon name="shield" size={17} />
              {t(token ? "disconnect" : "connect")}
            </button>
          </div>
        </header>
        <main>
          <section className="hero">
            <img src="/brand/heyface.png" alt="" />
            <div className="hero-content">
              <div className="hero-rule" />
              <h1>{t("heroTitle")}</h1>
              <p>{t("heroText")}</p>
              <span className="hero-chip">
                <Icon name="shield" size={15} />
                {t("local")}
              </span>
            </div>
          </section>
          <div className="section-heading">
            <div>
              <h2>{t(page)}</h2>
              <p>{t(domain === "people" ? "humanMode" : "animalMode")}</p>
            </div>
            {page !== "library" && (
              <div
                className="domain-switch"
                role="group"
                aria-label={t("method")}
              >
                <button
                  disabled={busy}
                  aria-pressed={domain === "people"}
                  onClick={() => changeDomain("people")}
                >
                  <Icon name="person" size={17} />
                  {t("people")}
                </button>
                <button
                  disabled={busy}
                  aria-pressed={domain === "animals"}
                  onClick={() => changeDomain("animals")}
                >
                  <Icon name="paw" size={17} />
                  {t("animals")}
                </button>
              </div>
            )}
          </div>
          {error && (
            <div className="notice error" role="alert">
              {error}
              <button aria-label={t("close")} onClick={() => setError("")}>
                <Icon name="close" size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="notice success" role="status">
              {notice}
            </div>
          )}
          {page === "library" ? (
            <section className="catalog">
              <MetadataFields
                fields={fields}
                setFields={setFields}
                domain={domain}
                page={page}
                t={t}
              />
              <button
                className="primary"
                disabled={busy}
                onClick={() => void loadRecords()}
              >
                {t("refresh")}
              </button>
              {records.length === 0 ? (
                <p className="catalog-empty">{t("recordsEmpty")}</p>
              ) : (
                <div className="record-list">
                  {records.map((record) => (
                    <button
                      key={record.id}
                      className="record-row"
                      onClick={() => setDetail({ person: record, score: 0 })}
                    >
                      <span className="initial">{record.name.slice(0, 1)}</span>
                      <strong>{record.name}</strong>
                      <span>
                        {record.city}, {record.state}
                      </span>
                      <Icon name="arrow" size={18} />
                    </button>
                  ))}
                </div>
              )}
              {cursor && (
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() => void loadRecords(true)}
                >
                  {t("loadMore")}
                </button>
              )}
            </section>
          ) : (
            <div className="workbench">
              <form className="query-panel" onSubmit={submit}>
                <div className="panel-heading">
                  <h3>{t("image")}</h3>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => void sample()}
                  >
                    {t("sample")}
                  </button>
                </div>
                <div
                  className={file ? "upload-zone has-image" : "upload-zone"}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    chooseFile(e.dataTransfer.files[0]);
                  }}
                >
                  <input
                    ref={input}
                    type="file"
                    accept="image/jpeg,image/png"
                    className="visually-hidden"
                    aria-label={t("choose")}
                    onChange={(e) => chooseFile(e.target.files?.[0])}
                  />
                  {preview ? (
                    <>
                      <img src={preview} alt={t("image")} />
                      <div className="image-toolbar">
                        <span>{file?.name}</span>
                        <button
                          type="button"
                          onClick={() => input.current?.click()}
                        >
                          {t("replace")}
                        </button>
                        <button
                          type="button"
                          aria-label={t("removeImage")}
                          onClick={() => setFile(null)}
                        >
                          <Icon name="close" size={16} />
                        </button>
                      </div>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="upload-trigger"
                      onClick={() => input.current?.click()}
                    >
                      <span className="upload-icon">
                        <Icon name="image" size={29} />
                      </span>
                      <strong>{t("choose")}</strong>
                      <span>{t("drag")}</span>
                      <small>{t("formats")}</small>
                    </button>
                  )}
                </div>
                {domain === "animals" && (
                  <>
                    <p className="helper">{t("animalHelp")}</p>
                    <label className="field">
                      {t("species")}
                      <select
                        value={species}
                        onChange={(e) => setSpecies(e.target.value)}
                      >
                        <option value="cat">{t("cat")}</option>
                        <option value="dog">{t("dog")}</option>
                        <option value="tiger">
                          {locale === "en" ? "Tiger" : "Tigre"}
                        </option>
                        <option value="zebra">Zebra</option>
                      </select>
                    </label>
                    <label className="checkbox">
                      <input
                        type="checkbox"
                        checked={cropConfirmed}
                        onChange={(e) => setCropConfirmed(e.target.checked)}
                      />
                      {t("animalConfirm")}
                    </label>
                  </>
                )}
                {(domain === "people" || page === "register") && (
                  <div className="filters-section">
                    <div className="panel-heading">
                      <h3>
                        {t(page === "register" ? "personDetails" : "filters")}
                      </h3>
                      {page === "search" && (
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => setFields(emptyFields)}
                        >
                          {t("clear")}
                        </button>
                      )}
                    </div>
                    {page === "search" && (
                      <p className="helper">{t("filterHelp")}</p>
                    )}
                    <MetadataFields
                      fields={fields}
                      setFields={setFields}
                      domain={domain}
                      page={page}
                      t={t}
                    />
                  </div>
                )}
                {page === "search" && (
                  <div className="search-options">
                    <label className="field">
                      {t("method")}
                      <select
                        value={method}
                        onChange={(e) => setMethod(e.target.value)}
                      >
                        {domain === "people" ? (
                          <>
                            <option value="facenet">FaceNet</option>
                            <option value="sface">SFace</option>
                          </>
                        ) : (
                          <>
                            <option value="dinov2">{t("global")}</option>
                            <option value="wildfusion">
                              {t("calibrated")}
                            </option>
                          </>
                        )}
                      </select>
                    </label>
                    <label
                      className="checkbox exact-option"
                      title={t("exactHelp")}
                    >
                      <input
                        type="checkbox"
                        checked={exact}
                        onChange={(e) => setExact(e.target.checked)}
                      />
                      {t("exact")}
                    </label>
                  </div>
                )}
                {method === "wildfusion" && (
                  <p className="helper">{t("calibrationNote")}</p>
                )}
                {page === "register" && (
                  <label className="checkbox consent">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                    />
                    {t("consent")}
                  </label>
                )}
                <button className="primary submit-button" disabled={busy}>
                  {busy ? (
                    <span className="spinner" />
                  ) : (
                    <Icon name={page === "register" ? "plus" : "search"} />
                  )}
                  <span>
                    {t(
                      busy
                        ? page === "register"
                          ? "saving"
                          : "processing"
                        : page,
                    )}
                  </span>
                  {!busy && <Icon name="arrow" size={18} />}
                </button>
              </form>
              <section className="results-panel" aria-live="polite">
                <div className="panel-heading">
                  <h3>{t("results")}</h3>
                  <span className="count">{result?.matches.length ?? "—"}</span>
                </div>
                {!result || result.matches.length === 0 ? (
                  <div className="empty-results">
                    <div className="scan-illustration">
                      <div className="scan-corner a" />
                      <div className="scan-corner b" />
                      <div className="scan-corner c" />
                      <div className="scan-corner d" />
                      <Icon
                        name={domain === "people" ? "person" : "paw"}
                        size={53}
                      />
                      <span />
                    </div>
                    <h4>{t(result ? "noResults" : "empty")}</h4>
                    <p>{t(result ? "noResultsHelp" : "emptyHelp")}</p>
                  </div>
                ) : (
                  <>
                    <p className="score-note">{t("scoreHelp")}</p>
                    <div className="matches">
                      {result.matches.map((match, index) => {
                        const entity = match.person ?? match.animal!;
                        return (
                          <button
                            className="match-row"
                            key={entity.id}
                            onClick={() => setDetail(match)}
                          >
                            <span className="rank">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <div className="match-content">
                              <strong>{entity.name}</strong>
                              <span>
                                {match.person
                                  ? `${match.person.city}, ${match.person.state}`
                                  : match.animal?.species}
                              </span>
                              <div className="score-track">
                                <i
                                  style={{
                                    width: `${Math.max(0, Math.min(1, match.score)) * 100}%`,
                                  }}
                                />
                              </div>
                            </div>
                            <div className="match-score">
                              <strong>{match.score.toFixed(4)}</strong>
                              <span>{t("score")}</span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                    {result.timing_ms && (
                      <div className="timings">
                        <span>{t("timings")}</span>
                        <strong>
                          {(
                            result.timing_ms.inference + result.timing_ms.search
                          ).toFixed(0)}{" "}
                          ms
                        </strong>
                      </div>
                    )}
                  </>
                )}
                <div className="results-footer">
                  <Icon name="shield" size={16} />
                  {t("privacy")}
                </div>
              </section>
            </div>
          )}
          <footer className="page-footer">
            <span>heyface.</span>
            <p>{t("footer")}</p>
          </footer>
        </main>
      </div>
      {showAccess && (
        <Dialog titleId="access-title" onClose={() => setShowAccess(false)}>
          <button
            className="modal-close"
            aria-label={t("close")}
            onClick={() => setShowAccess(false)}
          >
            <Icon name="close" />
          </button>
          <Icon name="shield" size={30} />
          <h2 id="access-title">{t("tokenTitle")}</h2>
          <p>{t("tokenHelp")}</p>
          <form onSubmit={connect}>
            <label className="field">
              {t("token")}
              <input
                ref={accessInput}
                type="password"
                autoComplete="off"
                required
                value={tokenDraft}
                onChange={(e) => setTokenDraft(e.target.value)}
              />
            </label>
            <p className="helper">{t("accessHint")}</p>
            <p className="helper">{t("tokenHint")}</p>
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" disabled={busy}>
              {t("connect")}
            </button>
          </form>
        </Dialog>
      )}
      {detail && (
        <Dialog titleId="detail-title" onClose={() => setDetail(null)}>
          <button
            className="modal-close"
            aria-label={t("close")}
            onClick={() => setDetail(null)}
          >
            <Icon name="close" />
          </button>
          <h2 id="detail-title">
            {detail.person?.name ?? detail.animal?.name}
          </h2>
          <dl>
            {detail.person && (
              <>
                <dt>{t("city")}</dt>
                <dd>
                  {detail.person.city}, {detail.person.state}
                </dd>
                <dt>{t("birth")}</dt>
                <dd>
                  {new Intl.DateTimeFormat(locale, {
                    timeZone: "UTC",
                  }).format(new Date(detail.person.birth_date + "T00:00:00Z"))}
                </dd>
                <dt>{t("facePoints")}</dt>
                <dd>{detail.person.face.landmarks.length}</dd>
              </>
            )}
            <dt>{t("dimensions")}</dt>
            <dd>
              {detail.person?.face.dimensions ??
                detail.animal?.representation.dimensions}
            </dd>
          </dl>
          <p className="helper">{t("scoreHelp")}</p>
          <button className="danger-button" onClick={() => void removeRecord()}>
            {t("deleteRecord")}
          </button>
        </Dialog>
      )}
    </div>
  );
}
