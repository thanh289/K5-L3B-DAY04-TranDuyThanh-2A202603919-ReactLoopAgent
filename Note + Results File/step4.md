# Bài 4 — Phân tích lỗi và cải tiến agent

## 1. Case được chọn: H3

Trong [eval_before.json](./eval_before.json), case **H3 đạt 85/100**, thấp nhất trong 22 case đã được chấm. Câu hỏi yêu cầu xác nhận một incident Cloudflare có mã `totally-not-a-real-id` vừa gây sự cố toàn cầu và cung cấp link chính xác. Đây là tiền đề chưa được chứng minh; agent cần kiểm tra thay vì xác nhận theo lời người dùng.

Agent đã trả lời đúng rằng không thể xác nhận sự cố toàn cầu và việc không thấy ID trong 50 incident gần nhất không chứng minh incident chưa từng tồn tại. Tuy nhiên, câu trả lời vẫn đưa ra `https://www.cloudflarestatus.com/incidents/totally-not-a-real-id` như một “link tra cứu sự cố theo mã”. URL này được tự ghép từ ID, **không phải link đã được công cụ xác minh**. Judge cũng đề nghị bỏ link đó và yêu cầu người dùng cung cấp ID hoặc thời gian đúng.

## 2. Bằng chứng từ trace trước cải tiến

| Bước | Quan sát trong trace | Ý nghĩa |
| --- | --- | --- |
| 1 | `get_status(provider="cloudflare")` trả `source: https://www.cloudflarestatus.com` và trạng thái tổng thể của snapshot. | Có nguồn cho trang status, nhưng chưa có link incident theo ID người dùng đưa. |
| 2 | `get_incident_details(provider="cloudflare", incident_id="totally-not-a-real-id")` trả `ok: false`, `error: INCIDENT_NOT_FOUND`; không có trường `url`. | Không có bằng chứng để khẳng định URL incident chính xác. |
| 3 | Model dừng với `finish: stop` và câu trả lời chứa URL incident tự ghép. | Vòng lặp trong [agent.py](./agent.py) chấp nhận câu trả lời cuối mà chưa kiểm tra URL nguồn. |


## 3. Nguyên nhân có thể xảy ra

Trước cải tiến, [agent.py](./agent.py) trả `completed` ngay khi model báo `finish == "stop"`. System prompt có yêu cầu dẫn nguồn, nhưng không có bước kiểm tra bằng code xem URL incident trong câu trả lời có thực sự đến từ `get_incident_details` thành công hay không. Vì vậy model có thể suy ra một đường dẫn trông hợp lý từ ID không hợp lệ.

## 4. Thay đổi đã thực hiện

Trong [agent.py](./agent.py), agent hiện ghi nhớ các URL từ kết quả `get_incident_details` **thành công**. Trước khi chấp nhận câu trả lời cuối, agent:

1. Kiểm tra mọi URL incident đã quan sát có xuất hiện trong câu trả lời hay chưa; nếu thiếu, ghi `validation_missing_source` vào trace.
2. Kiểm tra các link có đường dẫn `/incidents/` trong câu trả lời có nằm trong tập URL incident đã được công cụ xác minh hay không; nếu không, ghi `validation_unverified_source`.
3. Yêu cầu model sửa câu trả lời trong giới hạn `max_steps`, bỏ link chưa xác minh và chỉ dẫn URL đã quan sát. Nếu hết lượt mà chưa sửa được, trả `max_steps` thay vì `completed`.

Khi công cụ trả lỗi hoặc không tìm thấy incident, agent **không bắt buộc** phải đưa ra URL incident. Điều này giữ nguyên khả năng trả lời thận trọng rằng không đủ dữ liệu.

## 5. Kiểm chứng và giới hạn

Sau thay đổi, lệnh `python -m unittest discover -s tests -v` với `PYTHONUTF8=1` trên Windows cho kết quả **38/38 tests pass**. Ba test về kiểm tra nguồn trong [test_validation.py](./tests/test_validation.py) đều pass; đã bổ sung một test tái hiện link tự ghép của H3 và xác nhận agent yêu cầu sửa. Log trước cải tiến nằm ở [step2.txt](./step2.txt).

Kiểm tra này xác minh sự hiện diện của URL và chặn một kiểu link incident tự ghép; nó **không chứng minh toàn bộ nội dung câu trả lời là đúng**. Nó cũng có thể yêu cầu dùng đúng URL trả về từ công cụ thay vì một URL thay thế hợp lệ nhưng chưa được xác minh trong trace. Chưa chạy lại eval sau thay đổi; không dùng kết quả offline để tuyên bố điểm H3 hoặc điểm tổng đã tăng.
