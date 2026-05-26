function cloneDate(date: Date) {
    return new Date(date.getTime());
}

function startOfDay(date: Date) {
    const value = cloneDate(date);
    value.setHours(0, 0, 0, 0);
    return value;
}

function addDays(date: Date, days: number) {
    const value = cloneDate(date);
    value.setDate(value.getDate() + days);
    return value;
}

function endOfDay(date: Date) {
    const value = cloneDate(date);
    value.setHours(23, 59, 59, 0);
    return value;
}

function startOfWeek(date: Date) {
    const value = startOfDay(date);
    const day = value.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    return addDays(value, diff);
}

function startOfMonth(date: Date) {
    return new Date(date.getFullYear(), date.getMonth(), 1);
}

function endOfMonth(date: Date) {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0);
}

export const taskCreatedTimeShortcuts = [
    {
        text: "今日",
        value: () => {
            const today = new Date();
            return [startOfDay(today), endOfDay(today)];
        },
    },
    {
        text: "昨日",
        value: () => {
            const yesterday = addDays(new Date(), -1);
            return [startOfDay(yesterday), endOfDay(yesterday)];
        },
    },
    {
        text: "最近7天",
        value: () => {
            const now = new Date();
            return [startOfDay(addDays(now, -6)), now];
        },
    },
    {
        text: "最近30天",
        value: () => {
            const now = new Date();
            return [startOfDay(addDays(now, -29)), now];
        },
    },
    {
        text: "本周",
        value: () => {
            const now = new Date();
            return [startOfWeek(now), now];
        },
    },
    {
        text: "上周",
        value: () => {
            const currentWeekStart = startOfWeek(new Date());
            const previousWeekStart = addDays(currentWeekStart, -7);
            const previousWeekEnd = addDays(currentWeekStart, -1);
            return [startOfDay(previousWeekStart), endOfDay(previousWeekEnd)];
        },
    },
    {
        text: "本月",
        value: () => {
            const now = new Date();
            return [startOfMonth(now), now];
        },
    },
    {
        text: "上月",
        value: () => {
            const currentMonthStart = startOfMonth(new Date());
            const previousMonthDate = addDays(currentMonthStart, -1);
            return [startOfMonth(previousMonthDate), endOfDay(endOfMonth(previousMonthDate))];
        },
    },
];

export function dateRangeLabel(range: string[]) {
    if (!range.length) return "";
    if (range.length === 1 || range[0] === range[1]) return range[0];
    return `${range[0]} 至 ${range[1]}`;
}
