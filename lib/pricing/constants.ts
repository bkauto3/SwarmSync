export const TRIAL_DAYS = 14
export const MONEY_BACK_DAYS = 30
export const TRIAL_LABEL = `${TRIAL_DAYS}-day free trial`
export const MONEY_BACK_LABEL = `${MONEY_BACK_DAYS}-day money-back guarantee`

export const HERO_VALUE = 4300
export const HERO_ONE_TIME_PRICE = 299
export const PRICE_START = 149
export const PRICE_MAX = 799

export const FREE_CREDITS_LABEL = '$100 free credits'
export const NO_CARD_REQUIRED_LABEL = 'No credit card required'
export const CTA_TRIAL_BADGE = `${NO_CARD_REQUIRED_LABEL} • ${TRIAL_LABEL} • ${FREE_CREDITS_LABEL}`

export function formatCurrency(value: number) {
  return `$${value.toLocaleString('en-US')}`
}
