export type ScriptSegmentDraft = {
  id: string;
  title: string;
  body: string;
  excerpt: string;
  headingLevel: number | null;
  kind: "heading" | "lead";
};
