import { ApiError } from "@/lib/types";
import type {
  FooterLink,
  PageByRoleResponse,
  PublicCategory,
  PublicEntryDetail,
  PublicEntryListResponse,
} from "./types";

// Dữ liệu mock nội dung (NEXT_PUBLIC_USE_MOCK=1), sinh từ nội dung soạn sẵn
// `backend/apps/content/management/shop_content/*.json` qua bộ đổi `content_markup.py` (lô 5b, mkt-brand), biến thay như
// lệnh nạp khi chưa cấu hình: hotline "[hotline]", giữ hàng 30 phút, 1 kg, bước 0,5 kg. Mã thẻ hàng đổi sang mã của
// `lib/mock.ts` (CA-THU-KHUC, TOM-SU-TUOI, MUC-ONG; CUA-HOANG-DE luôn hết; MON-DA-NGUNG không có trong catalog = ngưng bán).
// Không ảnh ngoài, không tên/SĐT người thật. Ca lỗi: slug `bai-da-go` -> 410, slug không có -> 404.

export const MOCK_CATEGORIES: PublicCategory[] = [
  {
    "slug": "ra-dong",
    "name": "Rã đông",
    "description": "Cách rã đông từng loại hải sản cấp đông trước khi nấu."
  },
  {
    "slug": "mon-hap",
    "name": "Món hấp",
    "description": "Món hấp đơn giản từ cá, mực, tôm cấp đông."
  },
  {
    "slug": "mon-chien",
    "name": "Món chiên",
    "description": "Món chiên giòn, ít bắn dầu, làm nhanh trong bữa tối."
  }
];

export const MOCK_ENTRY_MAP: Record<string, PublicEntryDetail> = {
  "cach-mua-hang": {
    "kind": "page",
    "slug": "cach-mua-hang",
    "title": "Cách mua hàng",
    "seo_title": "Cách mua hàng ở Cá Về",
    "description": "Năm bước đặt hải sản cấp đông ở Cá Về: chọn món từ 1 kg, đặt hàng, chuyển khoản quét mã QR và nhận hàng tận nhà.",
    "excerpt": "Chọn món từ 1 kg, đặt hàng, quét mã QR để thanh toán, rồi nhận hàng tận nhà.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "5 bước đặt hàng"
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Chọn món.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Mỗi món mua từ 1 kg, thêm từng 0,5 kg. Combo mua theo combo."
              }
            ],
            [
              {
                "text": "Vào giỏ, bấm Đặt hàng.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Kiểm tra số kg và tạm tính. Có mã giảm giá thì nhập ở giỏ, mỗi đơn dùng 1 mã."
              }
            ],
            [
              {
                "text": "Nhập thông tin nhận hàng.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Họ tên, số điện thoại và địa chỉ giao hàng."
              }
            ],
            [
              {
                "text": "Quét mã QR để thanh toán.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Cá Về giữ hàng cho bạn 30 phút kể từ lúc bấm Đặt hàng."
              }
            ],
            [
              {
                "text": "Nhận hàng tận nhà.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Thanh toán xong, bạn vào thẳng trang đơn hàng để theo dõi. Cá Về giao hàng tận nhà bạn."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Câu hỏi thường gặp"
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Mua ít nhất bao nhiêu?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Mỗi món từ 1 kg, thêm từng 0,5 kg. Combo mua từ 1 combo."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Giao hàng có tốn thêm tiền không?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Không. Giá đã gồm giao hàng trong khu vực Phan Thiết. Bạn trả một lần khi quét mã QR, không trả thêm khi nhận hàng."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Hết 30 phút mà chưa thanh toán thì sao?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Đơn tự huỷ và hàng được giữ cho người khác. Bạn đặt lại đơn mới là được."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Đã chuyển khoản mà đơn chưa đổi trạng thái?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Đơn được xác nhận khi tiền về đủ. Nếu số tiền chưa khớp với đơn, Cá Về sẽ gọi cho bạn."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Xem lại đơn ở đâu?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Vào "
            },
            {
              "text": "Tra cứu đơn",
              "href": "/shop/orders/"
            },
            {
              "text": ", nhập mã đơn (bắt đầu bằng SO) và số điện thoại bạn đã dùng khi đặt."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Cá Về bán hàng gì?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Hải sản cấp đông, mua theo từng lô tại cảng. Nhận hàng xong, bạn cất ngay vào ngăn đá nếu chưa nấu."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Món đang hết hàng thì sao?"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Nguồn hàng theo mùa đánh bắt nên có lúc tạm hết. Bạn bấm \"Liên hệ chúng tôi\" để hỏi Cá Về."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "lien-he": {
    "kind": "page",
    "slug": "lien-he",
    "title": "Liên hệ",
    "seo_title": "Liên hệ Cá Về",
    "description": "Hotline, Zalo, email, địa chỉ kinh doanh và giờ làm việc của Cá Về.",
    "excerpt": "Gọi hotline, nhắn Zalo hoặc gửi email cho Cá Về. Hỏi về đơn hàng, bạn đọc mã đơn để Cá Về tra nhanh.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Hỏi về đơn hàng, bạn đọc mã đơn (bắt đầu bằng SO) để Cá Về tra nhanh."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Giờ làm việc"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "[giờ mở] – [giờ đóng], [ngày trong tuần]."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "gioi-thieu": {
    "kind": "page",
    "slug": "gioi-thieu",
    "title": "Giới thiệu Cá Về",
    "seo_title": "Giới thiệu Cá Về — Từ cảng về bếp nhà bạn",
    "description": "Cá Về mua hải sản theo từng lô tại cảng, bán hàng cấp đông theo kg và giao tận nhà ở Phan Thiết. Xem cách chúng tôi mua, bảo quản và giao hàng.",
    "excerpt": "Cá Về mua hải sản theo từng lô tại cảng, bán hàng cấp đông theo kg từ 1 kg và giao tận nhà bạn ở Phan Thiết.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về mua hải sản theo từng lô tại cảng, bán hàng cấp đông theo kg và giao tận nhà bạn."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Chúng tôi mua tại cảng, theo từng lô"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Nguồn hàng theo mùa đánh bắt. Cá Về mua theo từng lô tại cảng. Mỗi lô có mã và hạn dùng riêng, nên chúng tôi biết món bạn mua thuộc lô nào."
            }
          ]
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Mua theo lô tại cảng.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Mỗi lần mua là một lô riêng, có hạn dùng riêng."
              }
            ],
            [
              {
                "text": "Giữ đông theo lô.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Lô nào hạn dùng sớm hơn thì bán trước, để không lô nào nằm kho quá lâu."
              }
            ],
            [
              {
                "text": "Giao tận nhà.",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Cá Về giao hàng đến tận nhà bạn ở Phan Thiết."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Giá theo kg"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Mỗi món có một giá cho mỗi kg, combo có một giá cho mỗi combo. Tạm tính trong giỏ nhân giá với đúng số kg bạn chọn."
            }
          ]
        },
        {
          "type": "item_card",
          "item_code": "CA-THU-KHUC"
        },
        {
          "type": "item_card",
          "item_code": "MUC-ONG"
        },
        {
          "type": "item_card",
          "item_code": "CUA-HOANG-DE"
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Cấp đông theo lô, rã đông là nấu"
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Khi nhận hàng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cất ngay vào ngăn đá nếu chưa nấu. Hạn dùng ghi theo từng lô."
            }
          ]
        },
        {
          "type": "heading",
          "level": 3,
          "text": "Rã đông đúng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Chuyển xuống ngăn mát tủ lạnh trước khi nấu khoảng 8–12 giờ. Không ngâm nước nóng. Xem thêm ở "
            },
            {
              "text": "Rã đông cá đúng cách",
              "href": "/blog/?slug=ra-dong-ca-dung-cach"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Giao tận nhà ở Phan Thiết"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Đặt online, trả một lần bằng chuyển khoản quét mã QR. Giá đã gồm giao hàng, bạn không trả thêm khi nhận hàng. Xem "
            },
            {
              "text": "Chính sách giao hàng",
              "href": "/pages/?slug=giao-hang"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Hàng có vấn đề, báo Cá Về"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Nhận hàng có vấn đề, bạn gọi hoặc nhắn Zalo cho Cá Về, kèm mã đơn và ảnh hàng nhận được. Cách xử lý theo "
            },
            {
              "text": "Chính sách đổi trả và hoàn tiền",
              "href": "/pages/?slug=doi-tra"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Xem hàng đang có"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Giá ghi theo kg. Món tạm hết vẫn hiện để bạn gọi hỏi."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "doi-tra": {
    "kind": "page",
    "slug": "doi-tra",
    "title": "Chính sách đổi trả và hoàn tiền",
    "seo_title": "Chính sách đổi trả và hoàn tiền — Cá Về",
    "description": "Điều kiện đổi hàng, thời hạn báo, cách liên hệ và cách Cá Về xử lý số tiền đã chuyển khi đơn bị huỷ.",
    "excerpt": "Hàng có vấn đề khi nhận, bạn báo Cá Về kèm mã đơn và ảnh hàng nhận được. Cách xử lý xem ở trang này.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "1. Điều kiện đổi"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "[Hàng được đổi khi nào. Do legal-vn soạn, Lộc cung cấp sự thật.]"
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "2. Thời hạn báo"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Báo Cá Về trong [số] giờ sau khi nhận hàng."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "3. Cách liên hệ"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Gọi hotline hoặc nhắn Zalo cho Cá Về, kèm mã đơn (bắt đầu bằng SO) và ảnh hàng nhận được. Thông tin liên hệ ở trang "
            },
            {
              "text": "Liên hệ",
              "href": "/pages/?slug=lien-he"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "4. Xử lý tiền đã chuyển khi đơn huỷ"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Áp dụng khi đơn bị huỷ sau khi bạn đã chuyển khoản, gồm: Cá Về huỷ vì hàng không đạt chất lượng khi soạn, hết hàng hoặc không giao được; bạn đề nghị huỷ trước khi Cá Về bắt đầu soạn hàng; hoặc tiền của bạn về sau khi đơn đã tự huỷ vì quá thời gian giữ hàng."
            }
          ]
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Số tiền:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Cá Về trả lại toàn bộ số tiền của phần hàng không giao. Nếu chỉ một phần đơn bị huỷ, Cá Về trả lại đúng phần đó và vẫn giao phần còn lại. Bạn không mất phí cho việc trả lại."
              }
            ],
            [
              {
                "text": "Cách trả:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " chuyển khoản ngân hàng. Mặc định Cá Về chuyển về tài khoản bạn đã dùng để thanh toán. Nếu bạn muốn nhận ở tài khoản khác, nhân viên sẽ xác nhận với bạn qua điện thoại."
              }
            ],
            [
              {
                "text": "Thời hạn:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Cá Về gọi cho bạn trong 1 ngày làm việc kể từ khi đơn huỷ, và chuyển tiền trong 3 ngày làm việc kể từ khi hai bên thống nhất tài khoản nhận. Thời gian tiền về tài khoản tuỳ ngân hàng."
              }
            ],
            [
              {
                "text": "Liên hệ:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " gọi [hotline] hoặc nhắn Zalo [số Zalo], kèm mã đơn (bắt đầu bằng SO)."
              }
            ],
            [
              {
                "text": "Cá Về "
              },
              {
                "text": "không bao giờ",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " hỏi mã OTP, mật khẩu hay yêu cầu bạn chuyển thêm tiền để nhận lại tiền."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "5. Trường hợp không áp dụng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "[Do legal-vn soạn. Lộc xác nhận các trường hợp như hàng đã rã đông, bảo quản sai.]"
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "giao-hang": {
    "kind": "page",
    "slug": "giao-hang",
    "title": "Chính sách giao hàng",
    "seo_title": "Chính sách giao hàng — Cá Về",
    "description": "Khu vực giao, thời gian giao, giá đã gồm giao hàng và cách xử lý khi giao không thành công.",
    "excerpt": "Giao tận nhà trong khu vực Phan Thiết. Giá đã gồm giao hàng, bạn trả một lần khi quét mã QR, không trả thêm khi nhận hàng.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "1. Khu vực giao"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về giao tận nhà trong khu vực Phan Thiết. Địa chỉ ngoài khu vực này, Cá Về sẽ gọi trước khi soạn hàng; nếu không giao được, đơn được huỷ và bạn nhận lại toàn bộ số tiền đã trả."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "2. Thời gian giao"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về giao sau khi đơn đã thanh toán. [Thời gian giao dự kiến: chờ Lộc.] Trước khi giao, Cá Về có thể gọi xác nhận đơn."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "3. Giá đã gồm giao hàng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Giá trên Cá Về là giá cuối cùng, đã gồm giao hàng trong khu vực Phan Thiết. Bạn thanh toán một lần bằng chuyển khoản khi đặt hàng và không trả thêm cho người giao. Nếu sau này Cá Về tính thêm tiền giao hàng, khoản này sẽ hiện rõ trong tổng tiền trước khi bạn đặt hàng và được báo trên trang này trước khi áp dụng."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "4. Khi giao không thành công"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Nếu không gặp được bạn, Cá Về sẽ gọi để hẹn lại. [Số lần giao lại và cách xử lý khi không giao được. Do legal-vn soạn.]"
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "5. Khi nhận hàng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Bạn kiểm tra hàng lúc nhận. Hàng có vấn đề, xem "
            },
            {
              "text": "Chính sách đổi trả và hoàn tiền",
              "href": "/pages/?slug=doi-tra"
            },
            {
              "text": "."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "thanh-toan": {
    "kind": "page",
    "slug": "thanh-toan",
    "title": "Chính sách thanh toán",
    "seo_title": "Chính sách thanh toán — Cá Về",
    "description": "Cá Về nhận chuyển khoản ngân hàng quét mã QR, giữ hàng 30 phút, xác nhận khi tiền về đủ. Mỗi đơn dùng tối đa 1 mã giảm giá.",
    "excerpt": "Thanh toán một lần bằng chuyển khoản ngân hàng quét mã QR. Cá Về giữ hàng cho bạn 30 phút.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "1. Hình thức thanh toán"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về nhận một hình thức thanh toán: chuyển khoản ngân hàng bằng cách quét mã QR. Bạn trả đủ giá trị đơn trước khi giao. Cá Về không thu tiền khi giao hàng."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "2. Thời gian giữ hàng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Khi bạn bấm Đặt hàng, Cá Về giữ hàng cho đơn trong 30 phút. Quá 30 phút mà chưa nhận được tiền thì đơn tự huỷ."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "3. Xác nhận thanh toán"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Khi tiền về đủ, đơn được xác nhận tự động. Bạn xem trạng thái ở trang đơn hàng."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "4. Số tiền chưa khớp"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Nếu số tiền chuyển ít hơn giá trị đơn, đơn chưa được xác nhận tự động. Cá Về sẽ gọi cho bạn để xử lý. Nếu tiền về sau khi đơn đã huỷ, Cá Về cũng sẽ gọi cho bạn. Cách trả lại số tiền đã chuyển xem mục 4 của "
            },
            {
              "text": "Chính sách đổi trả và hoàn tiền",
              "href": "/pages/?slug=doi-tra"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "5. Mã giảm giá"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Mỗi đơn dùng tối đa 1 mã giảm giá. Mã không cộng dồn với ưu đãi khác; Cá Về tự chọn mức có lợi hơn cho bạn."
              }
            ],
            [
              {
                "text": "Mã chỉ dùng trong thời gian và với điều kiện ghi kèm mã. Mã có giới hạn tổng số lượt; hết lượt thì mã ngừng nhận dù chưa hết hạn. Mã không đổi ra tiền."
              }
            ],
            [
              {
                "text": "Số tiền giảm hiện trong tổng tiền trước khi bạn thanh toán."
              }
            ],
            [
              {
                "text": "Đơn quá 30 phút mà chưa thanh toán thì lượt dùng mã được trả lại. Đơn đã thanh toán rồi bị huỷ thì Cá Về trả lại đúng số tiền bạn đã thanh toán, lượt dùng mã không được trả lại."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "6. Hoá đơn"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cần hoá đơn mang tên công ty, bạn gọi [hotline] hoặc nhắn Zalo [số Zalo] kèm mã đơn (bắt đầu bằng SO) và tên công ty, mã số thuế, địa chỉ, email nhận hoá đơn, trước khi Cá Về giao hàng."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "quyen-rieng-tu": {
    "kind": "page",
    "slug": "quyen-rieng-tu",
    "title": "Chính sách quyền riêng tư",
    "seo_title": "Chính sách quyền riêng tư — Cá Về",
    "description": "Dữ liệu Cá Về thu khi bạn đặt hàng, bên cùng xử lý dữ liệu, nơi lưu, thời gian lưu và quyền của bạn.",
    "excerpt": "Cá Về thu dữ liệu gì khi bạn đặt hàng, dùng để làm gì, lưu ở đâu, lưu bao lâu và cách bạn yêu cầu xem, sửa, xoá.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "1. Dữ liệu Cá Về thu thập"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Khi bạn đặt hàng: họ tên, số điện thoại, địa chỉ giao hàng. Khi bạn chuyển khoản: thông tin giao dịch do ngân hàng ghi (số tiền, nội dung chuyển khoản, có thể có tên và số tài khoản người chuyển). Khi đơn bị huỷ sau khi bạn đã trả tiền: số tài khoản bạn chọn để nhận lại tiền."
            }
          ]
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về không thu ngày sinh, giấy tờ tuỳ thân hay dữ liệu vị trí từ thiết bị của bạn."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "2. Mục đích sử dụng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về dùng các dữ liệu này để giao hàng, gọi xác nhận đơn, xác nhận thanh toán và hỗ trợ bạn sau khi mua. [Câu chữ cuối do legal-vn soát.]"
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "3. Bên nhận hoặc xử lý dữ liệu cùng Cá Về"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Nhân viên Cá Về:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " chỉ người soạn hàng, giao hàng và chăm sóc đơn của bạn."
              }
            ],
            [
              {
                "text": "Google (Google Maps Platform, máy chủ ở nước ngoài):",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " chỉ khi bạn bấm \"Bản đồ\" để tìm địa chỉ. Google nhận chữ bạn gõ, vị trí bạn ghim, địa chỉ IP và thông tin trình duyệt. Cá Về không gửi họ tên hay số điện thoại cho Google. Google xử lý theo chính sách riêng của Google ("
              },
              {
                "text": "policies.google.com/privacy",
                "href": "https://policies.google.com/privacy"
              },
              {
                "text": "). Bạn có thể không dùng bản đồ và gõ địa chỉ trực tiếp."
              }
            ],
            [
              {
                "text": "SePay (đơn vị đối soát thanh toán) và ngân hàng:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " nhận mã đơn và số tiền để xác nhận bạn đã chuyển khoản."
              }
            ],
            [
              {
                "text": "Đơn vị cung cấp hạ tầng:",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " Google Cloud và Supabase, nơi đặt máy chủ lưu dữ liệu."
              }
            ],
            [
              {
                "text": "Cơ quan nhà nước có thẩm quyền",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " khi pháp luật yêu cầu."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "4. Lưu trữ ở nước ngoài"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Máy chủ lưu dữ liệu đơn hàng của Cá Về đặt tại Singapore. Cá Về áp dụng các biện pháp bảo mật: kết nối mã hoá HTTPS, phân quyền theo vai, không ghi dữ liệu cá nhân vào nhật ký hệ thống. [Câu về hồ sơ đánh giá tác động chuyển dữ liệu ra nước ngoài: chỉ thêm khi Cá Về đã nộp hồ sơ.]"
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "5. Lưu trên trình duyệt của bạn"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Shop lưu giỏ hàng (mã hàng và số lượng), các từ bạn tìm gần đây và mã tra đơn tạm thời trên chính trình duyệt của bạn để trang chạy đúng. Các thông tin này không chứa họ tên, số điện thoại hay địa chỉ, và Cá Về không thu về. Shop không dùng cookie quảng cáo hay công cụ theo dõi hành vi. Bạn có thể xoá bằng cách xoá dữ liệu trang web trong trình duyệt."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "6. Thời gian lưu"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Đơn hàng và chứng từ thanh toán được lưu theo thời hạn pháp luật về thương mại điện tử và kế toán yêu cầu ([thời hạn lưu: Duy điền sau khi kế toán chốt]). Hết thời hạn, Cá Về xoá hoặc ẩn danh họ tên, số điện thoại, địa chỉ."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "7. Quyền của bạn"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Muốn xem, sửa, xoá hoặc ngừng xử lý dữ liệu, bạn gọi [hotline] hoặc gửi email [email], kèm mã đơn (bắt đầu bằng SO) và số điện thoại đặt hàng để Cá Về xác minh. Cá Về xác nhận đã nhận yêu cầu trong [1 ngày làm việc] và trả lời trong [số ngày]."
            }
          ]
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Với đơn đã thanh toán, Cá Về giữ chứng từ theo quy định nhưng ẩn danh họ tên, số điện thoại, địa chỉ. Khiếu nại về dữ liệu cá nhân xử lý theo "
            },
            {
              "text": "Cơ chế giải quyết khiếu nại",
              "href": "/pages/?slug=khieu-nai"
            },
            {
              "text": "."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "dieu-khoan": {
    "kind": "page",
    "slug": "dieu-khoan",
    "title": "Điều kiện giao dịch chung",
    "seo_title": "Điều kiện giao dịch chung — Cá Về",
    "description": "Điều kiện áp dụng khi bạn đặt hàng trên website Cá Về: đặt hàng và giá, thanh toán, giao hàng, đổi trả và khiếu nại.",
    "excerpt": "Điều kiện áp dụng khi bạn đặt hàng trên website Cá Về: đặt hàng và giá, thanh toán, giao hàng, đổi trả, khiếu nại.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "1. Phạm vi áp dụng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Điều kiện này áp dụng khi bạn đặt hàng trên website Cá Về. Bạn không cần tạo tài khoản để đặt hàng. [Câu chữ cuối do legal-vn soạn.]"
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "2. Đặt hàng và giá"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Giá niêm yết theo kg, combo niêm yết theo combo. Mỗi món mua từ 1 kg, thêm từng 0,5 kg. Giá đã gồm giao hàng trong khu vực Phan Thiết. Nếu giá hoặc tình trạng hàng trong giỏ thay đổi, Shop báo cho bạn trước khi đặt. [Câu chữ cuối do legal-vn soạn.]"
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "3. Thanh toán"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Xem "
            },
            {
              "text": "Chính sách thanh toán",
              "href": "/pages/?slug=thanh-toan"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "4. Giao hàng"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Xem "
            },
            {
              "text": "Chính sách giao hàng",
              "href": "/pages/?slug=giao-hang"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "5. Đổi trả"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Xem "
            },
            {
              "text": "Chính sách đổi trả và hoàn tiền",
              "href": "/pages/?slug=doi-tra"
            },
            {
              "text": "."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "6. Khiếu nại và tranh chấp"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Xem "
            },
            {
              "text": "Cơ chế giải quyết khiếu nại",
              "href": "/pages/?slug=khieu-nai"
            },
            {
              "text": ". [Phần tranh chấp do legal-vn soạn.]"
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "khieu-nai": {
    "kind": "page",
    "slug": "khieu-nai",
    "title": "Cơ chế giải quyết khiếu nại",
    "seo_title": "Cơ chế giải quyết khiếu nại — Cá Về",
    "description": "Kênh gửi phản ánh, khiếu nại cho Cá Về, thời hạn phản hồi, các bước giải quyết và cách làm khi chưa thống nhất.",
    "excerpt": "Cách gửi phản ánh, khiếu nại cho Cá Về, thời hạn phản hồi và các bước giải quyết.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "1. Gửi phản ánh, khiếu nại"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Bạn chọn một trong các cách: gọi [hotline], nhắn Zalo [số Zalo] hoặc gửi email [email]. Thông tin ở trang "
            },
            {
              "text": "Liên hệ",
              "href": "/pages/?slug=lien-he"
            },
            {
              "text": ". Ghi mã đơn (bắt đầu bằng SO), số điện thoại đặt hàng, nội dung, kèm ảnh hoặc video nếu có."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "2. Thời hạn"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá Về phản hồi lần đầu trong vòng 2 giờ kể từ khi nhận phản ánh [trong giờ làm việc: chờ Duy xác nhận]."
            }
          ]
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Thời hạn dự kiến giải quyết:"
            }
          ]
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Hàng không đúng món, thiếu hoặc không đạt chất lượng khi nhận: [2 ngày làm việc]."
              }
            ],
            [
              {
                "text": "Trả lại tiền khi đơn huỷ: theo mục 4 của "
              },
              {
                "text": "Chính sách đổi trả và hoàn tiền",
                "href": "/pages/?slug=doi-tra"
              },
              {
                "text": "."
              }
            ],
            [
              {
                "text": "Giao trễ, không liên lạc được người giao: [1 ngày làm việc]."
              }
            ],
            [
              {
                "text": "Đã chuyển khoản nhưng đơn chưa xác nhận: [1 ngày làm việc]."
              }
            ],
            [
              {
                "text": "Dữ liệu cá nhân (xem, sửa, xoá): theo "
              },
              {
                "text": "Chính sách quyền riêng tư",
                "href": "/pages/?slug=quyen-rieng-tu"
              },
              {
                "text": "."
              }
            ],
            [
              {
                "text": "Việc khác: [5 ngày làm việc]."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "3. Trình tự"
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Cá Về ghi nhận yêu cầu."
              }
            ],
            [
              {
                "text": "Cá Về xác minh với bạn qua số điện thoại đặt hàng."
              }
            ],
            [
              {
                "text": "Cá Về đề xuất cách xử lý."
              }
            ],
            [
              {
                "text": "Cá Về thực hiện khi bạn đồng ý."
              }
            ],
            [
              {
                "text": "Cá Về báo kết quả cho bạn."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "4. Nếu chưa đồng ý với cách xử lý"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Hai bên tiếp tục thương lượng. Bạn có quyền nhờ hoà giải, hoặc yêu cầu cơ quan bảo vệ quyền lợi người tiêu dùng (Sở Công Thương [tỉnh/thành]) hỗ trợ, hoặc đưa ra trọng tài hay toà án theo Luật Bảo vệ quyền lợi người tiêu dùng."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "5. Người chịu trách nhiệm"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "[Tên doanh nghiệp], [địa chỉ kinh doanh], mã số thuế [mã số thuế]."
            }
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "thong-tin-nguoi-ban": {
    "kind": "page",
    "slug": "thong-tin-nguoi-ban",
    "title": "Thông tin người bán",
    "seo_title": "Thông tin người bán — Cá Về",
    "description": "Tên, mã số thuế, giấy chứng nhận đăng ký kinh doanh, địa chỉ và cách liên hệ đơn vị bán hàng trên website Cá Về.",
    "excerpt": "Thông tin đơn vị bán hàng trên website Cá Về.",
    "category": null,
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "Đơn vị bán hàng"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Tên: [tên doanh nghiệp]"
              }
            ],
            [
              {
                "text": "Loại hình: doanh nghiệp"
              }
            ],
            [
              {
                "text": "Giấy chứng nhận đăng ký doanh nghiệp số [số], do [nơi cấp] cấp ngày [ngày]"
              }
            ],
            [
              {
                "text": "Mã số thuế: [mã số thuế]"
              }
            ],
            [
              {
                "text": "Địa chỉ: [địa chỉ kinh doanh]"
              }
            ],
            [
              {
                "text": "Điện thoại: [hotline]"
              }
            ],
            [
              {
                "text": "Email: [email]"
              }
            ]
          ]
        }
      ]
    },
    "published_at": "2026-10-01T00:00:00Z",
    "updated_at": "2026-10-01T00:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T00:00:00Z",
    "author": "Cá Về"
  },
  "ra-dong-ca-dung-cach": {
    "kind": "post",
    "slug": "ra-dong-ca-dung-cach",
    "title": "Rã đông cá đúng cách để thịt không bở",
    "seo_title": "Rã đông cá đúng cách để thịt không bở | Cá Về",
    "description": "Rã đông cá cấp đông trong ngăn mát hoặc nước lạnh để thịt vẫn chắc. Những điều nên tránh khi rã đông cá.",
    "excerpt": "Ngăn mát hay nước lạnh, chọn cách nào cho từng món, và vì sao không nên dùng nước nóng.",
    "category": {
      "slug": "ra-dong",
      "name": "Rã đông"
    },
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Cá cấp đông rã đúng cách thì thịt vẫn chắc. Rã vội bằng nước nóng hay để ngoài lâu thì phần ngoài mềm nhũn trong khi lõi còn đá, nấu lên dễ bở."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Vì sao thịt cá bị bở"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Khi cá tan đá quá nhanh hoặc không đều, nước trong thớ thịt chảy ra ngoài. Thịt mất nước nên rời và bở khi nấu."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Cách 1: rã đông trong ngăn mát (nên dùng)"
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Để nguyên túi, đặt cá lên đĩa để hứng nước."
              }
            ],
            [
              {
                "text": "Chuyển xuống ngăn mát tủ lạnh trước khi nấu khoảng 8–12 giờ. Khúc dày cần lâu hơn."
              }
            ],
            [
              {
                "text": "Lấy ra, thấm khô mặt cá bằng khăn giấy rồi mới nấu."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Cách 2: khi cần gấp"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Ngâm "
              },
              {
                "text": "cả túi kín",
                "marks": [
                  "bold"
                ]
              },
              {
                "text": " trong nước lạnh. Không để nước lọt vào túi."
              }
            ],
            [
              {
                "text": "Thay nước lạnh khoảng 30 phút một lần."
              }
            ],
            [
              {
                "text": "Rã xong thì nấu ngay."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Những điều nên tránh"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Không ngâm nước nóng, không rã đông bằng vòi nước nóng."
              }
            ],
            [
              {
                "text": "Không để cá ngoài nhiệt độ phòng nhiều giờ."
              }
            ],
            [
              {
                "text": "Cá đã rã đông thì không cấp đông lại."
              }
            ]
          ]
        },
        {
          "type": "item_card",
          "item_code": "CA-THU-KHUC"
        }
      ]
    },
    "published_at": "2026-10-01T08:00:00Z",
    "updated_at": "2026-10-01T08:00:00Z",
    "version": 1,
    "effective_from": "2026-10-01T08:00:00Z",
    "author": "Cá Về"
  },
  "ra-dong-tom": {
    "kind": "post",
    "slug": "ra-dong-tom",
    "title": "Rã đông tôm mà vẫn giữ vị ngọt",
    "seo_title": "Rã đông tôm mà vẫn giữ vị ngọt | Cá Về",
    "description": "Cách rã đông tôm cấp đông trong ngăn mát hoặc nước lạnh để tôm không nhũn và giữ được vị.",
    "excerpt": "Để nguyên túi, rã trong ngăn mát hoặc nước lạnh, không xả nước trực tiếp lên tôm.",
    "category": {
      "slug": "ra-dong",
      "name": "Rã đông"
    },
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Tôm nhỏ và mỏng nên tan đá nhanh. Rã đúng cách giúp tôm không bị nhũn và giữ được vị."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Rã trong ngăn mát"
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Để nguyên túi, đặt lên đĩa."
              }
            ],
            [
              {
                "text": "Chuyển xuống ngăn mát tủ lạnh trước khi nấu khoảng 8–12 giờ."
              }
            ],
            [
              {
                "text": "Rã xong, để ráo rồi chế biến."
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Khi cần gấp"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "Ngâm cả túi kín trong âu nước lạnh, thay nước nếu nước bớt lạnh."
              }
            ],
            [
              {
                "text": "Không xả nước trực tiếp lên tôm đã bóc vỏ."
              }
            ],
            [
              {
                "text": "Rã xong thì nấu ngay, không cấp đông lại."
              }
            ]
          ]
        },
        {
          "type": "item_card",
          "item_code": "TOM-SU-TUOI"
        }
      ]
    },
    "published_at": "2026-10-02T08:00:00Z",
    "updated_at": "2026-10-02T08:00:00Z",
    "version": 1,
    "effective_from": "2026-10-02T08:00:00Z",
    "author": "Cá Về"
  },
  "muc-ong-hap-chien-hay-xao": {
    "kind": "post",
    "slug": "muc-ong-hap-chien-hay-xao",
    "title": "Mực ống: hấp, chiên hay xào?",
    "seo_title": "Mực ống: hấp, chiên hay xào? | Cá Về",
    "description": "Mực ống cấp đông nấu món gì: hấp gừng hành, chiên giòn hay xào lửa lớn. Cách cắt mực cho từng món.",
    "excerpt": "Mỗi cách nấu hợp với một kiểu cắt mực. Gợi ý nhanh để chọn món cho bữa tối.",
    "category": {
      "slug": "mon-hap",
      "name": "Món hấp"
    },
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Mực ống đã làm sạch chỉ cần rã đông, rửa lại là nấu được. Cách cắt quyết định món nào hợp hơn."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Hấp: để nguyên con hoặc cắt khoanh to"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Hấp cùng gừng và hành trong vài phút là chín. Hấp lâu mực sẽ dai."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Chiên: cắt khoanh tròn"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Thấm thật khô, lăn qua bột rồi chiên ngập dầu đến khi vàng. Mực càng khô thì càng ít bắn dầu."
            }
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Xào: khía vảy rồng, cắt miếng vừa ăn"
        },
        {
          "type": "paragraph",
          "children": [
            {
              "text": "Xào lửa lớn, nhanh tay, cho mực vào sau cùng để mực giòn."
            }
          ]
        },
        {
          "type": "quote",
          "children": [
            {
              "text": "Mực chín nhanh. Nấu quá lửa là cách dễ nhất làm mực dai."
            }
          ]
        },
        {
          "type": "item_card",
          "item_code": "MUC-ONG"
        }
      ]
    },
    "published_at": "2026-10-03T08:00:00Z",
    "updated_at": "2026-10-03T08:00:00Z",
    "version": 1,
    "effective_from": "2026-10-03T08:00:00Z",
    "author": "Cá Về"
  },
  "ca-thu-hap-gung-hanh": {
    "kind": "post",
    "slug": "ca-thu-hap-gung-hanh",
    "title": "Cá thu hấp gừng hành",
    "seo_title": "Cá thu hấp gừng hành | Cá Về",
    "description": "Cách làm cá thu hấp gừng hành cho 2–3 người từ cá thu cắt khúc cấp đông: nguyên liệu và 4 bước làm.",
    "excerpt": "Món hấp nhẹ cho bữa tối, không cần dầu chiên, làm trong khoảng nửa giờ.",
    "category": {
      "slug": "mon-hap",
      "name": "Món hấp"
    },
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "Nguyên liệu (2–3 người)"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "500 g cá thu cắt khúc, đã rã đông"
              }
            ],
            [
              {
                "text": "1 nhánh gừng, thái sợi"
              }
            ],
            [
              {
                "text": "3 cây hành lá"
              }
            ],
            [
              {
                "text": "Nước mắm, tiêu, một ít dầu ăn"
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Cách làm"
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Thấm khô cá, ướp chút nước mắm và tiêu khoảng 10 phút."
              }
            ],
            [
              {
                "text": "Xếp cá vào đĩa, rải gừng lên trên."
              }
            ],
            [
              {
                "text": "Hấp cách thuỷ đến khi thịt cá chuyển màu trắng đục và tách thớ."
              }
            ],
            [
              {
                "text": "Rắc hành lá, rưới một thìa dầu nóng lên trên rồi tắt bếp."
              }
            ]
          ]
        },
        {
          "type": "item_card",
          "item_code": "CA-THU-KHUC"
        },
        {
          "type": "item_card",
          "item_code": "CUA-HOANG-DE"
        },
        {
          "type": "item_card",
          "item_code": "MON-DA-NGUNG"
        }
      ]
    },
    "published_at": "2026-10-04T08:00:00Z",
    "updated_at": "2026-10-04T08:00:00Z",
    "version": 1,
    "effective_from": "2026-10-04T08:00:00Z",
    "author": "Cá Về"
  },
  "ca-thu-chien-sa-ot": {
    "kind": "post",
    "slug": "ca-thu-chien-sa-ot",
    "title": "Cá thu chiên sả ớt",
    "seo_title": "Cá thu chiên sả ớt | Cá Về",
    "description": "Cách làm cá thu chiên sả ớt cho 2–3 người từ cá thu cắt khúc cấp đông: nguyên liệu và 3 bước làm.",
    "excerpt": "Ướp sả ớt, chiên vàng hai mặt. Món đậm vị cho bữa cơm nhà.",
    "category": {
      "slug": "mon-chien",
      "name": "Món chiên"
    },
    "cover_image": null,
    "body": {
      "type": "doc",
      "blocks": [
        {
          "type": "heading",
          "level": 2,
          "text": "Nguyên liệu (2–3 người)"
        },
        {
          "type": "list",
          "ordered": false,
          "items": [
            [
              {
                "text": "500 g cá thu cắt khúc, đã rã đông"
              }
            ],
            [
              {
                "text": "3 cây sả băm nhỏ, 1–2 quả ớt"
              }
            ],
            [
              {
                "text": "Nước mắm, đường, dầu ăn"
              }
            ]
          ]
        },
        {
          "type": "heading",
          "level": 2,
          "text": "Cách làm"
        },
        {
          "type": "list",
          "ordered": true,
          "items": [
            [
              {
                "text": "Thấm khô cá, ướp nước mắm, chút đường và một nửa phần sả khoảng 15 phút."
              }
            ],
            [
              {
                "text": "Chiên cá vàng hai mặt rồi vớt ra."
              }
            ],
            [
              {
                "text": "Phi thơm phần sả còn lại với ớt, cho cá vào đảo nhẹ cho thấm."
              }
            ]
          ]
        },
        {
          "type": "item_card",
          "item_code": "CA-THU-KHUC"
        }
      ]
    },
    "published_at": "2026-10-05T08:00:00Z",
    "updated_at": "2026-10-05T08:00:00Z",
    "version": 1,
    "effective_from": "2026-10-05T08:00:00Z",
    "author": "Cá Về"
  }
};

// Đường dẫn cũ còn trong e2e cũ và `lib/mock.ts` (409 chính sách đổi phiên bản): trỏ về trang quyền riêng tư.
MOCK_ENTRY_MAP["chinh-sach-bao-mat"] = { ...MOCK_ENTRY_MAP["quyen-rieng-tu"], slug: "chinh-sach-bao-mat" };

/**
 * Bài mẫu chứa payload XSS/link độc (SR-24 F9). CHỈ để Playwright kiểm bộ hiển thị thân bài
 * (`ArticleBody` + `safeHref`): không `dialog`, không `<script>`, không `javascript:`, link ngoài
 * có `rel`. Mọi payload đặt cờ `window.__xss` thay vì `alert` để bắt được cả khi dialog bị chặn.
 * Không xuất hiện trong danh sách bài (không nằm trong `MOCK_ENTRY_MAP`). Đường vào: /blog/?slug=xss-mau
 */
export const XSS_SAMPLE_SLUG = "xss-mau";

const XSS_SAMPLE_ENTRY: PublicEntryDetail = {
  kind: "post",
  slug: XSS_SAMPLE_SLUG,
  title: "Bài thử XSS <script>window.__xss=1</script>",
  seo_title: "Bài thử XSS | Cá Về",
  description: "Bài mẫu kiểm thử an toàn nội dung (chỉ có ở bản mock).",
  excerpt: "Bài mẫu kiểm thử an toàn nội dung.",
  category: null,
  cover_image: null,
  body: {
    type: "doc",
    blocks: [
      { type: "heading", level: 2, text: "Tiêu đề <img src=x onerror=\"window.__xss=1\">" },
      {
        type: "paragraph",
        children: [
          { text: "<script>window.__xss=1</script> " },
          { text: "<img src=x onerror=\"window.__xss=1\"> ", marks: ["bold"] },
          { text: "</article><svg onload=window.__xss=1> " },
          { text: "&lt;b&gt;không phải thẻ&lt;/b&gt;" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "LINK-JS", href: "javascript:window.__xss=1" },
          { text: " " },
          { text: "LINK-JS-HOA", href: "JaVaScRiPt:window.__xss=1" },
          { text: " " },
          { text: "LINK-JS-TAB", href: "java\tscript:window.__xss=1" },
          { text: " " },
          { text: "LINK-DATA", href: "data:text/html;base64,PHNjcmlwdD53aW5kb3cuX194c3M9MTwvc2NyaXB0Pg==" },
          { text: " " },
          { text: "LINK-VB", href: " vbscript:msgbox(1)" },
          { text: " " },
          { text: "LINK-GIAO-THUC-TUONG-DOI", href: "//evil.example/phish" },
          { text: " " },
          { text: "LINK-GACH-NGUOC", href: "/\\evil.example" },
          { text: " " },
          { text: "LINK-GACH-NGUOC-DAU", href: "\\evil.example" },
          { text: " " },
          { text: "LINK-FILE", href: "file:///etc/passwd" },
        ],
      },
      {
        type: "paragraph",
        children: [
          { text: "LINK-NGOAI-OK", href: "https://example.com/bai-ngoai" },
          { text: " " },
          { text: "LINK-NGOAI-HTTP-OK", marks: ["bold"], href: "http://example.com/x" },
          { text: " " },
          { text: "LINK-NOI-BO-OK", href: "/shop/" },
          { text: " " },
          { text: "LINK-MAIL-OK", href: "mailto:hotro@example.com" },
          { text: " " },
          { text: "LINK-TEL-OK", href: "tel:0900000000" },
        ],
      },
      {
        type: "quote",
        children: [{ text: "<iframe src=\"javascript:window.__xss=1\"></iframe>", marks: ["italic"] }],
      },
      {
        type: "list",
        ordered: false,
        items: [
          [{ text: "<a href=\"javascript:window.__xss=1\">chữ thô</a>" }],
          [{ text: "MUC-LINK-JS", href: "javascript:window.__xss=1" }],
        ],
      },
      {
        type: "image",
        alt: "\"><script>window.__xss=1</script>",
        caption: "<img src=x onerror=\"window.__xss=1\"> chú thích",
        width: 1600,
        height: 1200,
        urls: {
          sm: "/favicon.ico?w=480",
          md: "/favicon.ico?w=960",
          lg: "/favicon.ico?w=1600",
        },
      },
      { type: "item_card", item_code: "X\"><img src=x onerror=window.__xss=1>" },
    ],
  },
  published_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T08:00:00Z",
  version: 1,
  effective_from: "2026-09-28T08:00:00Z",
  author: "Cá Về",
};

export function mockGetPublicEntry(slug: string): PublicEntryDetail {
  if (slug === "bai-da-go") {
    throw new ApiError("Bài này không còn trên web.", 410);
  }
  const entry = slug === XSS_SAMPLE_SLUG ? XSS_SAMPLE_ENTRY : MOCK_ENTRY_MAP[slug];
  if (!entry) {
    throw new ApiError("Không tìm thấy bài.", 404);
  }
  return entry;
}

export function mockGetPublicEntries(params?: { category?: string; page?: number }): PublicEntryListResponse {
  let list = Object.values(MOCK_ENTRY_MAP)
    .filter((e) => e.kind === "post")
    .sort((a, b) => b.published_at.localeCompare(a.published_at))
    .map((e) => ({
      slug: e.slug,
      title: e.title,
      excerpt: e.excerpt,
      category: e.category,
      cover_image: e.cover_image,
      published_at: e.published_at,
    }));
  if (params?.category) {
    list = list.filter((e) => e.category?.slug === params.category);
  }
  return { results: list, count: list.length, total: list.length, page: params?.page || 1, total_pages: 1 };
}

export function mockGetPublicCategories(): PublicCategory[] {
  return MOCK_CATEGORIES;
}

const ROLE_SLUGS: Record<string, string> = {
  refund: "doi-tra",
  shipping: "giao-hang",
  payment: "thanh-toan",
  privacy: "quyen-rieng-tu",
  terms: "dieu-khoan",
  complaints: "khieu-nai",
  seller_info: "thong-tin-nguoi-ban",
};

export function mockGetPageByRole(role: string): PageByRoleResponse {
  const slug = ROLE_SLUGS[role];
  const entry = slug ? MOCK_ENTRY_MAP[slug] : undefined;
  if (!entry) throw new ApiError("Không tìm thấy trang chính sách.", 404);
  return { slug: entry.slug, title: entry.title, version: 1, version_id: 101, effective_from: entry.effective_from };
}

// Khớp 6 trang chính sách ở footer (06-marketing B4, thứ tự 1→6), giống `features/site/mock.ts`.
export function mockGetFooterLinks(): FooterLink[] {
  return ["doi-tra", "giao-hang", "thanh-toan", "quyen-rieng-tu", "dieu-khoan", "khieu-nai"].map((slug) => ({
    title: MOCK_ENTRY_MAP[slug].title,
    slug,
  }));
}
