export type RuntimeTopicCursor = {
  lastEventId: string | null;
  afterSequence: number | null;
};

export type RuntimeTopicSubscription = RuntimeTopicCursor & {
  topic: string;
};

export type RuntimeEventDto = {
  schemaVersion: 1;
  eventId: string;
  eventType: string;
  topic: string;
  sequence: number;
  occurredAt: string;
  accountId: string | null;
  resourceType: string | null;
  resourceId: string | null;
  taskId: string | null;
  revision: number;
  payload: Record<string, unknown>;
};

export type RuntimeSubscribedFrame = {
  type: "subscribed";
  subscriptionRevision: number;
  topics: Array<{
    topic: string;
    currentSequence: number;
    replayedCount: number;
  }>;
};

export type RuntimeSyncRequiredFrame = {
  type: "sync.required";
  subscriptionRevision: number;
  topic: string;
  currentSequence: number;
  reason: string;
};

export type RuntimeSocketErrorFrame = {
  type: "error";
  errorCode: string;
  message: string;
  subscriptionRevision: number;
};

export type RuntimeSocketStatus =
  | "idle"
  | "connecting"
  | "online"
  | "offline"
  | "error";
