import { formatDate } from '@angular/common';

// Formate date in ddmmyyy hhmm formate
export class DateUtils {
    static format(
        value: string | Date | null | undefined,
        format = 'dd/MM/yyyy HH:mm'
    ): string {
        if (!value) {
            return '-';
        }

        return formatDate(value, format, 'en-IN');
    }
}
