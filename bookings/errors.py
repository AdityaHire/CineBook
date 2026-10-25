class CenebookError(Exception):
    code = "INTERNAL_ERROR"
    status = 500
    message = "An unexpected error occurred."
    details = None

    def __init__(self, message=None, details=None):
        if message:
            self.message = message
        if details is not None:
            self.details = details
        super().__init__(self.message)

    def as_dict(self):
        err = {"code": self.code, "message": self.message}
        if self.details is not None:
            err["details"] = self.details
        return {"error": err}


class ShowNotFound(CenebookError):
    code = "SHOW_NOT_FOUND"
    status = 404
    message = "Show not found."


class ShowNotBookable(CenebookError):
    code = "SHOW_NOT_BOOKABLE"
    status = 409
    message = "Booking for this show is closed or cancelled."


class InvalidSeats(CenebookError):
    code = "INVALID_SEATS"
    status = 400
    message = "Invalid seat selection."


class TooManySeats(CenebookError):
    code = "TOO_MANY_SEATS"
    status = 400
    message = "You can select up to 8 seats."

    def __init__(self, max_seats=8):
        super().__init__(details={"max": max_seats})


class SeatUnavailable(CenebookError):
    code = "SEAT_UNAVAILABLE"
    status = 409
    message = "One or more selected seats are no longer available."

    def __init__(self, seats=None, message=None):
        if seats:
            seat_str = ", ".join(seats)
            msg = f"Seat {seat_str} is no longer available. Please choose another."
            super().__init__(message=msg, details={"seats": seats})
        else:
            super().__init__(message=message or self.message)


class HoldExpired(CenebookError):
    code = "HOLD_EXPIRED"
    status = 409
    message = "Your seat hold has expired. Please select seats again."


class InvalidRequest(CenebookError):
    code = "INVALID_REQUEST"
    status = 400
    message = "Invalid request payload."


class PaymentFailed(CenebookError):
    code = "PAYMENT_FAILED"
    status = 402
    message = "Payment failed. Your seats are still held. Try again."


class BookingNotFound(CenebookError):
    code = "BOOKING_NOT_FOUND"
    status = 404
    message = "Booking not found."


class AlreadyCancelled(CenebookError):
    code = "ALREADY_CANCELLED"
    status = 409
    message = "This booking has already been cancelled."


class CancellationNotAllowed(CenebookError):
    code = "CANCELLATION_NOT_ALLOWED"
    status = 409
    message = "Cancellation is only allowed up to 2 hours before showtime."

    def __init__(self, cutoff_hours=2, message=None):
        super().__init__(message=message or self.message, details={"cutoff_hours": cutoff_hours})
