"""Pydantic response models for the API, so the OpenAPI schema describes the payloads."""

from pydantic import BaseModel, ConfigDict


class Explanation(BaseModel):
    """Why a coin was picked: score breakdown plus its rank inside its bucket."""

    model_config = ConfigDict(extra="allow")

    summary: str
    base: float
    history_adjustment: float
    news_adjustment: float
    news_headline: str | None = None
    news_sentiment: str | None = None
    rsi: float
    rsi_adjustment: float
    macd: float
    signal: float
    macd_adjustment: float
    score: float
    bucket_size: int
    bucket_rank: int
    bucket_avg_score: float


class Pick(BaseModel):
    coin: str
    display_name: str
    type: str
    price: float
    score: float
    rsi: float
    variance: float
    explanation: Explanation | None = None


class NewsItem(BaseModel):
    title: str
    link: str
    source: str
    timestamp: float


class SentimentImpact(BaseModel):
    coin: str
    headline: str
    polarity: float
    adjustment: float
    sentiment: str


class EvaluationResult(BaseModel):
    timestamp: float
    performance: dict[str, float]


class HistoryRecord(BaseModel):
    """One saved portfolio. Older records have no ``picks`` or ``performance``."""

    model_config = ConfigDict(extra="allow")

    timestamp: float
    portfolio: list[str]
    entry_prices: dict[str, float] = {}
    evaluated: bool = False
    performance: dict[str, float] | None = None
    picks: list[Pick] | None = None


class GenerateResponse(BaseModel):
    evaluation_results: list[EvaluationResult]
    held_evaluations: int
    news: list[NewsItem]
    sentiment_impacts: list[SentimentImpact]
    portfolio: list[Pick]
    mock: bool
