-- phpMyAdmin SQL Dump
-- version 4.8.3
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Jun 18, 2020 at 05:24 PM
-- Server version: 5.7.30-0ubuntu0.18.04.1
-- PHP Version: 7.2.24-0ubuntu0.18.04.6

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET AUTOCOMMIT = 0;
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `ecolife_tuvan`
--

-- --------------------------------------------------------

--
-- Table structure for table `authentication`
--

CREATE TABLE `authentication` (
  `authen_id` int(11) NOT NULL,
  `authen_username` varchar(200) DEFAULT NULL,
  `authen_email` varchar(200) DEFAULT NULL,
  `authen_phone` varchar(200) DEFAULT NULL,
  `authen_pass` text,
  `authen_token` text,
  `authen_group` int(11) DEFAULT NULL,
  `authen_note` text,
  `authen_parent` int(11) DEFAULT NULL,
  `authen_time` int(11) DEFAULT NULL,
  `authen_online` int(11) DEFAULT NULL,
  `authen_status` int(1) DEFAULT NULL,
  `authen_active` int(1) DEFAULT NULL,
  `authen_img` varchar(200) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `authentication`
--

INSERT INTO `authentication` (`authen_id`, `authen_username`, `authen_email`, `authen_phone`, `authen_pass`, `authen_token`, `authen_group`, `authen_note`, `authen_parent`, `authen_time`, `authen_online`, `authen_status`, `authen_active`, `authen_img`) VALUES
(1, 'Root', NULL, NULL, '$2y$10$WxvMeDnkTvVoqy7uJfRSzunc3fwKaoqF3VxHF4brpTxtizGoLZTXa', NULL, NULL, NULL, NULL, NULL, 1592472999, NULL, NULL, NULL),
(4, 'vender', 'vietlinhvu007@gmail.com', '+84375829464', '$2y$10$oa9xbDsmXdQJUdyQhY/i9ul0MPqJx9tLG5F37q3A7Sm0jmAtL4PqW', NULL, 2, NULL, NULL, 1591672339, 1592473602, 1, 1, NULL),
(5, 'vendor2', 'congmt@viettel.com.vn', '0984100148', '$2y$10$pWunvR77F34MyRqR/ojmO.XjiYUfQ.TWIrlByBGpu55LENeMIGSLi', NULL, 2, NULL, NULL, 1592384863, 1592385509, 1, 1, NULL),
(6, 'vendor3', NULL, NULL, '$2y$10$3C4fTGu88VvWGdmGVHtW/.g36r794LEP0CT9FhZRU5TorfU7s7X9O', NULL, 2, NULL, NULL, 1592386036, 1592386159, 1, 1, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `companies`
--

CREATE TABLE `companies` (
  `company_uid` bigint(15) NOT NULL,
  `company_name` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `company_fullname` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `company_image` text COLLATE utf8_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Dumping data for table `companies`
--

INSERT INTO `companies` (`company_uid`, `company_name`, `company_fullname`, `company_image`) VALUES
(4, 'Nhà Xinh', 'Công ty TNHH Nội Thất Nhà Xinh', 'http://nte3.ecolife.com/Local/companies/company_image/4/nha-xinh-logo.jpg'),
(5, 'Nội Thất Đương Đại', 'Công ty TNHH Nội Thất Đương Đại', 'http://nte3.ecolife.com/Local/companies/company_image/5/logo-duong-dai.png'),
(6, 'Nhà Đẹp', 'Công ty TNHH Thương mại và Nội thất Nhà Đẹp', 'http://nte3.ecolife.com/Local/companies/company_image/6/noi-that-nha-dep.png');

-- --------------------------------------------------------

--
-- Table structure for table `control`
--

CREATE TABLE `control` (
  `control_name` varchar(150) COLLATE utf8_vietnamese_ci NOT NULL,
  `control_value` text COLLATE utf8_vietnamese_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_vietnamese_ci;

--
-- Dumping data for table `control`
--

INSERT INTO `control` (`control_name`, `control_value`) VALUES
('defaultVoucher', '100000'),
('startCampaign', '1591850040'),
('stopCampaign', '1593491640'),
('tokenKey', 'J8Cn3aQmolyXgfajgkhlotiu8MRi9yCkp06WHq');

-- --------------------------------------------------------

--
-- Table structure for table `customers`
--

CREATE TABLE `customers` (
  `cus_id` varchar(150) COLLATE utf8_vietnamese_ci NOT NULL,
  `cus_tower` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_home` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_name` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_email` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_phone` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_gender` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_birthday` varchar(150) COLLATE utf8_vietnamese_ci DEFAULT NULL,
  `cus_token` text COLLATE utf8_vietnamese_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_vietnamese_ci;

--
-- Dumping data for table `customers`
--

INSERT INTO `customers` (`cus_id`, `cus_tower`, `cus_home`, `cus_name`, `cus_email`, `cus_phone`, `cus_gender`, `cus_birthday`, `cus_token`) VALUES
('1234567890', '', '', 'John Doe', 'vietlinhvu007@gmail.com', '', '', '', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `mailer`
--

CREATE TABLE `mailer` (
  `mail_id` int(11) NOT NULL,
  `mail_mailer` varchar(200) DEFAULT NULL,
  `mail_name` varchar(200) DEFAULT NULL,
  `mail_config` text,
  `mail_weight` int(11) DEFAULT NULL,
  `mail_used` int(11) DEFAULT NULL,
  `mail_free` int(11) DEFAULT NULL,
  `mail_limit` int(11) DEFAULT NULL,
  `mail_target` int(5) DEFAULT NULL,
  `mail_active` int(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `mailer_result`
--

CREATE TABLE `mailer_result` (
  `mresult_id` bigint(15) NOT NULL,
  `mresult_mailer` varchar(150) DEFAULT NULL,
  `mresult_content` text,
  `mresult_to` varchar(150) DEFAULT NULL,
  `mresult_from` varchar(150) DEFAULT NULL,
  `mresult_time` int(11) DEFAULT NULL,
  `mresult_result` int(1) DEFAULT NULL,
  `mresult_log` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `notice`
--

CREATE TABLE `notice` (
  `notice_id` bigint(15) NOT NULL,
  `notice_time` int(11) DEFAULT NULL,
  `notice_uid` bigint(15) DEFAULT NULL,
  `notice_uname` varchar(200) DEFAULT NULL,
  `notice_fire_uid` int(11) DEFAULT NULL,
  `notice_fire_uname` varchar(200) DEFAULT NULL,
  `notice_content` text,
  `notice_variable` text,
  `notice_seen` int(1) DEFAULT NULL,
  `notice_level` int(2) DEFAULT NULL,
  `notice_action` text,
  `notice_type` varchar(150) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `orders`
--

CREATE TABLE `orders` (
  `order_id` int(11) NOT NULL,
  `order_cid` bigint(15) DEFAULT NULL,
  `order_cname` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `order_reciever_name` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `order_reciever_phone` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `order_reciever_email` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `order_reciever_home` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `order_pid` bigint(15) DEFAULT NULL,
  `order_pname` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `order_time` int(11) DEFAULT NULL,
  `order_value` int(11) DEFAULT NULL,
  `order_status` int(1) DEFAULT NULL,
  `order_note` text COLLATE utf8_unicode_ci,
  `order_node_admin` text COLLATE utf8_unicode_ci,
  `order_uid` bigint(15) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Dumping data for table `orders`
--

INSERT INTO `orders` (`order_id`, `order_cid`, `order_cname`, `order_reciever_name`, `order_reciever_phone`, `order_reciever_email`, `order_reciever_home`, `order_pid`, `order_pname`, `order_time`, `order_value`, `order_status`, `order_note`, `order_node_admin`, `order_uid`) VALUES
(2, 1234567890, 'John Doe', 'John Doe', '0965690599', 'vietlinhvu007@gmail.com', NULL, 15923649514092, 'Gói thiết kế mẫu 01', 1592469219, 34000000, 1, NULL, NULL, 4);

-- --------------------------------------------------------

--
-- Table structure for table `products`
--

CREATE TABLE `products` (
  `product_id` bigint(15) NOT NULL,
  `product_name` varchar(150) COLLATE utf8_unicode_ci DEFAULT NULL,
  `product_image` text COLLATE utf8_unicode_ci,
  `product_voucher` text COLLATE utf8_unicode_ci,
  `product_price` int(11) DEFAULT NULL,
  `product_bom` text COLLATE utf8_unicode_ci,
  `product_element` text COLLATE utf8_unicode_ci,
  `product_uid` bigint(15) DEFAULT NULL,
  `product_desc` text COLLATE utf8_unicode_ci,
  `product_weight` bigint(15) DEFAULT NULL,
  `product_public` int(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Dumping data for table `products`
--

INSERT INTO `products` (`product_id`, `product_name`, `product_image`, `product_voucher`, `product_price`, `product_bom`, `product_element`, `product_uid`, `product_desc`, `product_weight`, `product_public`) VALUES
(15923649514092, 'Gói thiết kế mẫu 01', 'http://nte3.ecolife.com/Local/products/product_image/4/download.jpg', 'Giảm giá 10% khi đặt hàng', 34000000, 'http://nte3.ecolife.com/Local/products/product_bom/4/BigDataUniversity BD0111EN Certificate _ Cognitive Class.pdf', 'Bàn, Ghế, Đèn trần', 4, '<p style=\"background-color:rgb(255, 255, 255);\" positionable=\"true\"><strong>Bàn ghế gỗ phòng khách đơn giản hiện đại BPK07</strong></p><p style=\"background-color:rgb(255, 255, 255);\" positionable=\"true\"><a href=\"https://hoaphathanoi.vn/category/ban-ghe-salon-tiep-khach\">Bàn ghế gỗ phòng khách đơn giản hiện đại</a>&nbsp;BPK07&nbsp;là bộ bàn ghế phòng khách gỗ kiểu góc chữ L do nội thất sinh liên trực tiếp sản xuất. Bộ bàn ghế thường được kê ở vị trí góc của không gian phòng khách làm cho không gian phòng khách được sang trọng và tiết kệm được diện tích không gian phòng khách.</p><figure class=\"image magic_widget\" style=\"width:500px;position:relative;background-color:rgb(255, 255, 255);\" contenteditable=\"false\" positionable=\"true\"><img class=\"ck_image\" style=\"width:100%;\" src=\"https://hoaphathanoi.vn/media/product/2444435_ban_ghe_go_phong_khach_don_gian_hien_dai_bpk07.jpg\"></figure><p style=\"background-color:rgb(255, 255, 255);\" positionable=\"true\">-Bộ bàn ghế&nbsp;gỗ&nbsp;phòng khách&nbsp;BPK07 được làm hoàn toàn bằng gỗ tự nhiên như gỗ xoan đào hoặc gỗ sồi tùy chọn.</p><p style=\"background-color:rgb(255, 255, 255);\" positionable=\"true\">-Bộ bàn ghế&nbsp;gỗ đơn giàn&nbsp;BPK07 bao gồm 2 băng ghế dài xếp thành chữ L và 2 ghế đôn gỗ, kính mặt bàn mài trơn dày&nbsp; 8 ly.</p><p style=\"background-color:rgb(255, 255, 255);\" positionable=\"true\">-Ghế sofa gỗ chữ L&nbsp; dài 2,3 m&nbsp; rộng 2 m, bàn chính dài 1m1 x rộng 70cm x ao50cm, 2 ghế đôn vuông 35cm&nbsp;</p><p style=\"background-color:rgb(255, 255, 255);\" positionable=\"true\"><strong>Tags:</strong> <a href=\"https://hoaphathanoi.vn/tag/bo-ban-ghe-sofa-go-phong-khach\">bộ bàn ghế sofa gỗ phòng khách</a>, <a href=\"https://hoaphathanoi.vn/tag/bo-ban-ghe-sofa-go-gia-re\">bộ bàn ghế sofa gỗ giá rẻ</a>, <a href=\"https://hoaphathanoi.vn/tag/bo-ban-ghe-sofa-go-chu-l\">bộ bàn ghế sofa gỗ chữ l</a>, <a href=\"https://hoaphathanoi.vn/tag/bo-ban-ghe-sofa-go-cao-cap\">bộ bàn ghế sofa gỗ cao cấp</a>, <a href=\"https://hoaphathanoi.vn/tag/bo-ban-ghe-sofa-go-dep\">bộ bàn ghế sofa gỗ đẹp</a>, <a href=\"https://hoaphathanoi.vn/tag/ban-ghe-sofa-go-phong-khach\">bàn ghế sofa gỗ phòng khách</a>, <a href=\"https://hoaphathanoi.vn/tag/ban-ghe-sofa-go-hien-dai\">bàn ghế sofa gỗ hiện đại</a>, <a href=\"https://hoaphathanoi.vn/tag/ban-ghe-sofa-go-phong-khach-hien-dai\">bàn ghế sofa gỗ phòng khách hiện đại</a>, <a href=\"https://hoaphathanoi.vn/tag/ban-ghe-go-phong-khach-don-gian-hien-dai\">bàn ghế gỗ phòng khách đơn giản hiện đại</a>, <a href=\"https://hoaphathanoi.vn/tag/ban-ghe-go-sofa-chu-l\">bàn ghế gỗ sofa chữ l</a>,</p>', NULL, 0);

-- --------------------------------------------------------

--
-- Table structure for table `product_images`
--

CREATE TABLE `product_images` (
  `product_img_id` int(11) NOT NULL,
  `product_img_pid` bigint(15) DEFAULT NULL,
  `product_img_path` text COLLATE utf8_vietnamese_ci,
  `product_img_weight` bigint(15) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_vietnamese_ci;

--
-- Dumping data for table `product_images`
--

INSERT INTO `product_images` (`product_img_id`, `product_img_pid`, `product_img_path`, `product_img_weight`) VALUES
(17, 15923649514092, 'http://nte3.ecolife.com/Local/product_images/product_img_path/4/images (1).jpg', NULL),
(18, 15923649514092, 'http://nte3.ecolife.com/Local/product_images/product_img_path/4/images.jpg', NULL),
(19, 15923649514092, 'http://nte3.ecolife.com/Local/product_images/product_img_path/4/images (1).jpg', NULL),
(20, 15923649514092, 'http://nte3.ecolife.com/Local/product_images/product_img_path/4/images.jpg', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `uploader_disks`
--

CREATE TABLE `uploader_disks` (
  `disk_id` int(11) NOT NULL,
  `disk_uploader` varchar(200) DEFAULT NULL,
  `disk_name` varchar(200) DEFAULT NULL,
  `disk_type` varchar(200) DEFAULT NULL,
  `disk_config` text,
  `disk_weight` int(11) DEFAULT NULL,
  `disk_total` bigint(200) DEFAULT NULL,
  `disk_used` bigint(200) DEFAULT NULL,
  `disk_free` bigint(200) DEFAULT NULL,
  `disk_active` int(1) DEFAULT NULL,
  `disk_target` int(2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `uploader_disks`
--

INSERT INTO `uploader_disks` (`disk_id`, `disk_uploader`, `disk_name`, `disk_type`, `disk_config`, `disk_weight`, `disk_total`, `disk_used`, `disk_free`, `disk_active`, `disk_target`) VALUES
(2, 'http://nte3.ecolife.com', 'Local', 'local', '{\"driver\":\"local\",\"root\":\"/var/www/html/ecolife_banhang_nte3/storage/app/\"}', 1, 52572946432, 40040657995, 12532288437, 1, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `uploader_files`
--

CREATE TABLE `uploader_files` (
  `file_id` int(11) NOT NULL,
  `file_uploader` varchar(200) DEFAULT NULL,
  `file_disk` varchar(200) DEFAULT NULL,
  `file_table` varchar(200) DEFAULT NULL,
  `file_column` varchar(200) DEFAULT NULL,
  `file_uid` varchar(200) DEFAULT NULL,
  `file_name` varchar(200) DEFAULT NULL,
  `file_path` varchar(200) DEFAULT NULL,
  `file_size` bigint(15) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Dumping data for table `uploader_files`
--

INSERT INTO `uploader_files` (`file_id`, `file_uploader`, `file_disk`, `file_table`, `file_column`, `file_uid`, `file_name`, `file_path`, `file_size`) VALUES
(49, 'http://nte3.ecolife.com', 'Local', 'companies', 'company_image', '4', 'default.png', 'http://nte3.ecolife.com/Local/companies/company_image/4/default.png', 5062),
(50, 'http://nte3.ecolife.com', 'Local', 'products', 'product_image', '4', 'download.jpg', 'http://nte3.ecolife.com/Local/products/product_image/4/download.jpg', 10021),
(51, 'http://nte3.ecolife.com', 'Local', 'product_images', 'product_img_path', '4', 'images.jpg', 'http://nte3.ecolife.com/Local/product_images/product_img_path/4/images.jpg', 5189),
(52, 'http://nte3.ecolife.com', 'Local', 'product_images', 'product_img_path', '4', 'images (1).jpg', 'http://nte3.ecolife.com/Local/product_images/product_img_path/4/images (1).jpg', 6861),
(53, 'http://nte3.ecolife.com', 'Local', 'products', 'product_bom', '4', 'BigDataUniversity BD0111EN Certificate _ Cognitive Class.pdf', 'http://nte3.ecolife.com/Local/products/product_bom/4/BigDataUniversity BD0111EN Certificate _ Cognitive Class.pdf', 239221),
(54, 'http://nte3.ecolife.com', 'Local', 'companies', 'company_image', '4', 'download.jpg', 'http://nte3.ecolife.com/Local/companies/company_image/4/download.jpg', 10021),
(55, 'http://nte3.ecolife.com', 'Local', 'companies', 'company_image', '4', 'logo-duong-dai.png', 'http://nte3.ecolife.com/Local/companies/company_image/4/logo-duong-dai.png', 3345),
(56, 'http://nte3.ecolife.com', 'Local', 'companies', 'company_image', '4', 'nha-xinh-logo.jpg', 'http://nte3.ecolife.com/Local/companies/company_image/4/nha-xinh-logo.jpg', 6107),
(57, 'http://nte3.ecolife.com', 'Local', 'companies', 'company_image', '5', 'logo-duong-dai.png', 'http://nte3.ecolife.com/Local/companies/company_image/5/logo-duong-dai.png', 3345),
(58, 'http://nte3.ecolife.com', 'Local', 'companies', 'company_image', '6', 'noi-that-nha-dep.png', 'http://nte3.ecolife.com/Local/companies/company_image/6/noi-that-nha-dep.png', 2743);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `authentication`
--
ALTER TABLE `authentication`
  ADD PRIMARY KEY (`authen_id`),
  ADD UNIQUE KEY `authen_username` (`authen_username`),
  ADD UNIQUE KEY `authen_email` (`authen_email`),
  ADD UNIQUE KEY `authen_phone` (`authen_phone`),
  ADD KEY `authen_group` (`authen_group`),
  ADD KEY `authen_parent` (`authen_parent`),
  ADD KEY `authen_time` (`authen_time`),
  ADD KEY `authen_online` (`authen_online`),
  ADD KEY `authen_active` (`authen_active`),
  ADD KEY `authen_img` (`authen_img`),
  ADD KEY `authen_status` (`authen_status`);

--
-- Indexes for table `companies`
--
ALTER TABLE `companies`
  ADD UNIQUE KEY `company_uid` (`company_uid`),
  ADD KEY `company_name` (`company_name`),
  ADD KEY `company_fullname` (`company_fullname`);

--
-- Indexes for table `control`
--
ALTER TABLE `control`
  ADD PRIMARY KEY (`control_name`);

--
-- Indexes for table `customers`
--
ALTER TABLE `customers`
  ADD UNIQUE KEY `cus_id` (`cus_id`),
  ADD KEY `cus_home` (`cus_home`),
  ADD KEY `cus_email` (`cus_email`),
  ADD KEY `cus_tower` (`cus_tower`),
  ADD KEY `cus_birthday` (`cus_birthday`),
  ADD KEY `cus_gender` (`cus_gender`);

--
-- Indexes for table `mailer`
--
ALTER TABLE `mailer`
  ADD PRIMARY KEY (`mail_id`),
  ADD UNIQUE KEY `mail_username` (`mail_name`),
  ADD KEY `mail_weight` (`mail_weight`),
  ADD KEY `mail_used` (`mail_used`),
  ADD KEY `mail_free` (`mail_free`),
  ADD KEY `mail_limit` (`mail_limit`),
  ADD KEY `mail_target` (`mail_target`),
  ADD KEY `mail_active` (`mail_active`),
  ADD KEY `mail_mailer` (`mail_mailer`);

--
-- Indexes for table `mailer_result`
--
ALTER TABLE `mailer_result`
  ADD PRIMARY KEY (`mresult_id`),
  ADD KEY `m_result_mailer` (`mresult_mailer`),
  ADD KEY `m_result_to` (`mresult_to`),
  ADD KEY `m_result_from` (`mresult_from`),
  ADD KEY `m_result_time` (`mresult_time`),
  ADD KEY `m_result_result` (`mresult_result`);

--
-- Indexes for table `notice`
--
ALTER TABLE `notice`
  ADD PRIMARY KEY (`notice_id`),
  ADD KEY `notice_seen` (`notice_seen`),
  ADD KEY `notice_uid` (`notice_uid`),
  ADD KEY `notice_uname` (`notice_uname`),
  ADD KEY `notice_time` (`notice_time`),
  ADD KEY `notice_level` (`notice_level`),
  ADD KEY `notice_fire_uid` (`notice_fire_uid`),
  ADD KEY `notice_fire_uname` (`notice_fire_uname`),
  ADD KEY `notice_type` (`notice_type`);

--
-- Indexes for table `orders`
--
ALTER TABLE `orders`
  ADD PRIMARY KEY (`order_id`),
  ADD KEY `order_cid` (`order_cid`),
  ADD KEY `order_cname` (`order_cname`),
  ADD KEY `order_pid` (`order_pid`),
  ADD KEY `order_pname` (`order_pname`),
  ADD KEY `order_time` (`order_time`),
  ADD KEY `order_value` (`order_value`),
  ADD KEY `order_status` (`order_status`),
  ADD KEY `order_uid` (`order_uid`),
  ADD KEY `order_reciever_name` (`order_reciever_name`),
  ADD KEY `order_reciever_phone` (`order_reciever_phone`),
  ADD KEY `order_reciever_email` (`order_reciever_email`),
  ADD KEY `order_reciever_home` (`order_reciever_home`);

--
-- Indexes for table `products`
--
ALTER TABLE `products`
  ADD PRIMARY KEY (`product_id`),
  ADD KEY `product_name` (`product_name`),
  ADD KEY `product_price` (`product_price`),
  ADD KEY `product_uid` (`product_uid`),
  ADD KEY `product_weight` (`product_weight`),
  ADD KEY `product_public` (`product_public`);

--
-- Indexes for table `product_images`
--
ALTER TABLE `product_images`
  ADD PRIMARY KEY (`product_img_id`),
  ADD KEY `product_img_pid` (`product_img_pid`),
  ADD KEY `product_img_weight` (`product_img_weight`);

--
-- Indexes for table `uploader_disks`
--
ALTER TABLE `uploader_disks`
  ADD PRIMARY KEY (`disk_id`),
  ADD UNIQUE KEY `disk_name` (`disk_name`),
  ADD KEY `disk_type` (`disk_type`),
  ADD KEY `disk_weight` (`disk_weight`),
  ADD KEY `disk_total` (`disk_total`),
  ADD KEY `disk_used` (`disk_used`),
  ADD KEY `disk_free` (`disk_free`),
  ADD KEY `disk_active` (`disk_active`),
  ADD KEY `disk_target` (`disk_target`),
  ADD KEY `disk_uploader` (`disk_uploader`);

--
-- Indexes for table `uploader_files`
--
ALTER TABLE `uploader_files`
  ADD PRIMARY KEY (`file_id`),
  ADD KEY `file_uploader` (`file_uploader`),
  ADD KEY `file_disk` (`file_disk`),
  ADD KEY `file_table` (`file_table`),
  ADD KEY `file_column` (`file_column`),
  ADD KEY `file_uid` (`file_uid`),
  ADD KEY `file_path` (`file_path`),
  ADD KEY `file_size` (`file_size`),
  ADD KEY `file_name` (`file_name`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `authentication`
--
ALTER TABLE `authentication`
  MODIFY `authen_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `mailer`
--
ALTER TABLE `mailer`
  MODIFY `mail_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `mailer_result`
--
ALTER TABLE `mailer_result`
  MODIFY `mresult_id` bigint(15) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `notice`
--
ALTER TABLE `notice`
  MODIFY `notice_id` bigint(15) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `orders`
--
ALTER TABLE `orders`
  MODIFY `order_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `products`
--
ALTER TABLE `products`
  MODIFY `product_id` bigint(15) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15923649514093;

--
-- AUTO_INCREMENT for table `product_images`
--
ALTER TABLE `product_images`
  MODIFY `product_img_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT for table `uploader_disks`
--
ALTER TABLE `uploader_disks`
  MODIFY `disk_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `uploader_files`
--
ALTER TABLE `uploader_files`
  MODIFY `file_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=59;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
