import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

// 30 AI messages per user per hour
export const chatRatelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(30, "1 h"),
});
