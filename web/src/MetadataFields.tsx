import type { Message } from "./i18n";

export const emptyFields = {
  name: "",
  sex: "",
  birth_date: "",
  state: "",
  city: "",
};
export type Metadata = typeof emptyFields;
type Props = {
  fields: Metadata;
  setFields: (value: Metadata) => void;
  domain: "people" | "animals";
  page: "search" | "register" | "library";
  t: (message: Message) => string;
};

export function MetadataFields({ fields, setFields, domain, page, t }: Props) {
  const fieldLabel: Record<keyof Metadata, Message> = {
    name: "name",
    sex: "sex",
    birth_date: "birth",
    state: "state",
    city: "city",
  };
  return (
    <div className="fields">
      {(Object.keys(fields) as (keyof typeof fields)[])
        .filter((key) => domain === "people" || key === "name")
        .map((key) => (
          <label
            key={key}
            className={key === "name" ? "field name-field" : "field"}
          >
            {t(fieldLabel[key])}
            {key === "sex" ? (
              <select
                value={fields.sex}
                onChange={(e) => setFields({ ...fields, sex: e.target.value })}
              >
                <option value="">
                  {page === "register" ? t("unspecified") : t("any")}
                </option>
                {(["female", "male", "other", "unspecified"] as const).map(
                  (value) => (
                    <option key={value} value={value}>
                      {t(value)}
                    </option>
                  ),
                )}
              </select>
            ) : (
              <input
                value={fields[key]}
                type={key === "birth_date" ? "date" : "text"}
                maxLength={key === "name" ? 160 : 120}
                required={page === "register"}
                onChange={(e) =>
                  setFields({ ...fields, [key]: e.target.value })
                }
              />
            )}
          </label>
        ))}
    </div>
  );
}
