import type { Message } from "./i18n";
import { Icon } from "./Icon";

type Props = {
  t: (message: Message) => string;
  connected: boolean;
  onConnect: () => void;
  onTry: (domain: "people" | "animals") => void;
};
const REPOSITORY = "https://github.com/flaviotinococoutinho/heyface";

export function StartPage({ t, connected, onConnect, onTry }: Props) {
  return (
    <div className="start-page">
      <section className="intro">
        <div className="intro-copy">
          <h1>{t("startTitle")}</h1>
          <p>{t("startText")}</p>
          <a className="text-link" href="#first-test">
            {t("firstTest")}
          </a>
        </div>
        <div className="intro-image">
          <img src="/brand/heyface.png" alt="" />
          <span>{t("exampleIdentity")}</span>
        </div>
      </section>
      <section
        className="first-test"
        id="first-test"
        aria-labelledby="first-test-title"
      >
        <div>
          <h2 id="first-test-title">{t("firstTest")}</h2>
          <p>{t("firstTestHelp")}</p>
        </div>
        <ol className="trial-steps">
          <li>
            <strong>{t("prepareExamples")}</strong>
            <span>{t("prepareHelp")}</span>
            <code>./heyface demo</code>
          </li>
          <li>
            <strong>{t("connectEnvironment")}</strong>
            <span>{t("connectHelp")}</span>
            <button
              className="text-link"
              disabled={connected}
              onClick={onConnect}
            >
              {t(connected ? "connected" : "connect")}
            </button>
          </li>
          <li>
            <strong>{t("chooseScenario")}</strong>
            <span>{t("scenarioHelp")}</span>
          </li>
        </ol>
      </section>
      <section className="scenarios" aria-label={t("chooseScenario")}>
        <article className="scenario people-scenario">
          <Icon name="person" size={25} />
          <h2>{t("peopleScenario")}</h2>
          <p>{t("peopleScenarioHelp")}</p>
          <ul>
            <li>{t("peopleValueOne")}</li>
            <li>{t("peopleValueTwo")}</li>
          </ul>
          <button className="primary" onClick={() => onTry("people")}>
            {t("tryPerson")}
          </button>
        </article>
        <article className="scenario animal-scenario">
          <div className="animal-portrait">
            <img src="/brand/animal.png" alt="" loading="lazy" />
          </div>
          <div className="animal-scenario-copy">
            <Icon name="paw" size={25} />
            <h2>{t("animalScenario")}</h2>
            <p>{t("animalScenarioHelp")}</p>
            <button className="primary" onClick={() => onTry("animals")}>
              {t("tryAnimal")}
            </button>
          </div>
        </article>
      </section>
      <section className="pilot-note">
        <div>
          <h2>{t("pilotTitle")}</h2>
          <p>{t("pilotHelp")}</p>
        </div>
        <a
          className="text-link"
          href={`${REPOSITORY}/blob/main/docs/pilot.md`}
          target="_blank"
          rel="noreferrer"
        >
          {t("pilotLink")}
        </a>
      </section>
      <section className="integration-note">
        <div>
          <h2>{t("integrationTitle")}</h2>
          <p>{t("integrationHelp")}</p>
        </div>
        <div className="integration-links">
          <a href="/api/v1/openapi.json" target="_blank" rel="noreferrer">
            {t("apiContract")}
          </a>
          <a
            href={`${REPOSITORY}/blob/main/docs/flutter.md`}
            target="_blank"
            rel="noreferrer"
          >
            {t("flutterGuide")}
          </a>
          <a href={REPOSITORY} target="_blank" rel="noreferrer">
            {t("sourceCode")}
          </a>
        </div>
      </section>
    </div>
  );
}
