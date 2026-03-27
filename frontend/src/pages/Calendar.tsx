import { useQuery } from "@tanstack/react-query";
import { getCalendar } from "../api";
import { format, isToday, isTomorrow } from "date-fns";
import { CalendarDays } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  applied: "border-blue-600",
  screen: "border-yellow-500",
  interview: "border-purple-500",
  offer: "border-emerald-500",
};

export default function CalendarPage() {
  const { data: events = [] } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => getCalendar().then((r) => r.data),
  });

  function label(date: Date) {
    if (isToday(date)) return "Today";
    if (isTomorrow(date)) return "Tomorrow";
    return format(date, "EEE d MMM");
  }

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-semibold">Calendar</h2>

      {events.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-600 gap-3">
          <CalendarDays size={40} />
          <p className="text-sm">No upcoming events. Add next actions to your applications.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((event: any) => {
            const date = new Date(event.date);
            return (
              <div
                key={event.id}
                className={`bg-gray-900 border-l-4 ${STATUS_COLORS[event.status] ?? "border-gray-700"} border border-gray-800 rounded-xl p-4 flex items-center justify-between`}
              >
                <div>
                  <p className="font-medium text-white">{event.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5 capitalize">{event.status}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-300">{label(date)}</p>
                  <p className="text-xs text-gray-500">{format(date, "HH:mm")}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
