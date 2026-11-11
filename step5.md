# Bài 5 — Fix 1

## Cấu hình và kết quả đã có

Hai file `eval_before.json` và `eval_after.json` đều chấm đủ 22/22 case với OpenAI `gpt-6-luna` cho agent và judge, `max_steps=8`, dataset `core`. Điểm tổng giảm từ **97,09** xuống **95,45** (−1,64). Đây là hai lần chạy độc lập với judge LLM, nên chênh lệch nhỏ chưa chứng minh thay đổi chất lượng ổn định.

| Case | Trước | Sau | Chênh lệch |
|---|---:|---:|---:|
| E1 | 100 | 99 | −1 |
| E2 | 100 | 100 | 0 |
| E3 | 100 | 100 | 0 |
| E4 | 100 | 100 | 0 |
| E5 | 99 | 93 | −6 |
| E6 | 100 | 100 | 0 |
| A1 | 96 | 100 | +4 |
| A2 | 100 | 100 | 0 |
| A3 | 99 | 98 | −1 |
| A4 | 100 | 100 | 0 |
| A5 | 99 | 99 | 0 |
| A6 | 94 | 95 | +1 |
| A7 | 100 | 100 | 0 |
| A8 | 95 | 100 | +5 |
| H1 | 89 | 94 | +5 |
| H2 | 100 | 95 | −5 |
| H3 | 85 | 50 | −35 |
| H4 | 100 | 100 | 0 |
| H5 | 95 | 89 | −6 |
| H6 | 93 | 95 | +2 |
| H7 | 99 | 98 | −1 |
| H8 | 93 | 95 | +2 |

Agent gọi model **66 → 60** lần; token agent **73.839 → 63.384**, token judge **45.164 → 43.986**, tổng **119.003 → 107.370**.

## Trace H3 và nguyên nhân

- Lần trước: `get_status(cloudflare)` → `get_incident_details(cloudflare, totally-not-a-real-id)` trả `INCIDENT_NOT_FOUND` → câu trả lời thận trọng nhưng tự dựng URL incident; judge chấm 85.
- Lần sau: chỉ `get_status(cloudflare)` → trả lời không thấy ID trong danh sách, không dựng URL. Judge thô chấm 86, nhưng kiểm tra cơ học phát hiện thiếu `get_incident_details` và **chặn điểm ở 50**. `get_status` chỉ hiển thị tối đa 5 incident khớp, không phải phép tra ID trực tiếp.
- Sửa trong `agent.py`: với câu hỏi nêu rõ mã incident, prompt yêu cầu tra ID; trước khi chấp nhận câu trả lời cuối, agent kiểm tra đã gọi `get_incident_details` cho đúng mã chưa. Nếu chưa, ghi `validation_missing_incident_lookup` vào trace và yêu cầu model gọi tool trong giới hạn bước. Không cài sẵn ID, URL hay câu trả lời H3.


# Báo cáo Bài 5 — Fix 2


| Chỉ số | Trước | Sau | Chênh lệch |
|---|---:|---:|---:|
| Điểm trung bình /100 | 97,09 | **97,41** | **+0,32** |
| Lần gọi model của agent | 66 | 61 | −5 |
| Lần gọi tool | 59 | 49 | −10 |
| Token agent | 73.839 | 63.181 | −10.658 |
| Token judge | 45.164 | 40.420 | −4.744 |
| Tổng token ghi nhận | 119.003 | 103.601 | −15.402 |

## Điểm từng case

| Case | Trước | Sau | Chênh lệch | Case | Trước | Sau | Chênh lệch |
|---|---:|---:|---:|---|---:|---:|---:|
| E1 | 100 | 89 | −11 | E2 | 100 | 100 | 0 |
| E3 | 100 | 100 | 0 | E4 | 100 | 97 | −3 |
| E5 | 99 | 95 | −4 | E6 | 100 | 100 | 0 |
| A1 | 96 | 100 | +4 | A2 | 100 | 100 | 0 |
| A3 | 99 | 100 | +1 | A4 | 100 | 100 | 0 |
| A5 | 99 | 98 | −1 | A6 | 94 | 93 | −1 |
| A7 | 100 | 99 | −1 | A8 | 95 | 100 | +5 |
| H1 | 89 | 92 | +3 | H2 | 100 | 100 | 0 |
| H3 | 85 | 99 | +14 | H4 | 100 | 100 | 0 |
| H5 | 95 | 91 | −4 | H6 | 93 | 92 | −1 |
| H7 | 99 | 99 | 0 | H8 | 93 | 99 | +6 |

## Trace đáng chú ý

- **H3, 85 → 99:** Trước đó agent gọi `get_incident_details` cho mã không tồn tại nhưng tự dựng URL. Lần sau tool trả `INCIDENT_NOT_FOUND`; trace ghi `validation_unverified_source` khi model thử dẫn URL không xác minh. Câu trả lời cuối không còn URL tự dựng và đề nghị cung cấp ID hoặc thời gian đúng. Tuy nhiên, câu trả lời cuối rất ngắn, không nhắc rõ giới hạn 50 incident và không nói trực tiếp rằng chưa thể xác nhận sự cố toàn cầu. Điểm 99 của judge vì thế nên đọc cùng câu trả lời thực tế, không xem là bằng chứng mọi yêu cầu đã được đáp ứng hoàn hảo.
- **H1, 89 → 92:** Lần sau đọc incident GitHub `h02n9572mx9y`, theo liên kết đến `xr3myzj7ms51`, rồi đọc incident Cloudflare `yaa0witbl2me`; có URL riêng cho từng bản ghi và kết luận không có bằng chứng chung nguyên nhân. Model calls giảm 6 → 4, tool calls 6 → 4. Judge còn lưu ý câu mở đầu hơi gộp thời điểm snapshot với thời điểm xảy ra; mô tả backlog/queue time Cloudflare không tự chứng minh nguyên nhân hay toàn bộ phạm vi ảnh hưởng.
- **A5, 99 → 98:** Lần sau chỉ dùng hai lần `get_status` và kết luận không thể lập danh sách đầy đủ incident Actions năm 2025 từ phạm vi 50 incident gần nhất; không bịa danh sách hoặc suy ra năm 2025 không có sự cố. Model calls giảm 6 → 3, tool calls 5 → 2. Câu “các kết quả hiển thị đều thuộc tháng 11/2026” chỉ được hỗ trợ cho các incident thực sự hiển thị, không phải toàn bộ 23 kết quả khớp.
- **E1, 100 → 89:** Giảm điểm lớn nhất còn lại. Agent vẫn báo đúng Actions operational và các incident đã resolved, nhưng mô tả “4–7/11” dễ khiến người đọc hiểu ảnh hưởng kéo dài đến ngày 7; trace chỉ ghi các khoảng ảnh hưởng ngày 4/11 và cập nhật resolved ngày 7/11. Một incident Actions cũng được diễn đạt như sự cố riêng biệt dù bản ghi dẫn tới incident tổng hợp.
- **A1/A8/H8:** Lần sau tăng lần lượt +4/+5/+6 nhờ đối chiếu phạm vi và giới hạn dữ liệu tốt hơn. **E4/E5/H5** giảm lần lượt −3/−4/−4, chủ yếu do câu trả lời dài hoặc diễn đạt mốc snapshot, phạm vi, thời gian ảnh hưởng chưa thật chính xác.
