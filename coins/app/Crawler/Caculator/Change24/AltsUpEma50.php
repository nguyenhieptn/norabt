<?php

namespace App\Crawler\Caculator\Change24;

use App\Helpers\DB\Models;
use App\Helpers\Request\Query;
use App\Helpers\Request\Reply;

class AltsUpEma50
{

    function __construct()
    {
    }

    public static function caculate($N, &$startObjectIndex)
    {



        $model = Models::get('Admin/Change_24h');

        $index = "altsup50_" . $N;

        if (!isset($startObjectIndex[$index]) || $startObjectIndex[$index] == null) {

            echo "Caculate start object for $index\n";

            $columnName = [
                'CHANGE24H_UP50_EMA' => 'change24h_up50_ema' . $N,
                'CHANGE24H_UP50_EMA5' => 'change24h_up50_ema5',
                'CHANGE24H_UP50_EMA9' => 'change24h_up50_ema9',
                'CHANGE24H_UP50_EMA13' => 'change24h_up50_ema13'
            ];

            $firstEmas = $model->read([[[$columnName['CHANGE24H_UP50_EMA'], '>', 0]]], function ($db) use ($N, $columnName) {
                $db->orderBy(CHANGE24H_TIME, 'DESC')->limit(1);
            });

            if (!$firstEmas['result']) return $firstEmas;

            if (isset($firstEmas['data'][0])) {
                $startObjectIndex[$index] = $firstEmas['data'][0];
            }

            if (!isset($startObjectIndex[$index])) {

                $firstEmas = $model->read([[[CHANGE24H_UP50, '>', 0]]], function ($db) use ($N) {
                    $db->orderBy(CHANGE24H_TIME, 'ASC')->limit($N);
                });

                $firstEmas = $firstEmas['data'];

                if (count($firstEmas) == $N) {
                    $avg = 0;
                    foreach ($firstEmas as $item) {
                        $avg += (float)$item->{CHANGE24H_UP50} / $N;
                    }
                    $firstEma = $avg;

                    $startObjectIndex[$index] = $firstEmas[$N - 1];

                    $model->edit([
                        DATA_KEY => [[[CHANGE24H_ID, '=', $item->{CHANGE24H_ID}]]],
                        DATA_EDITOR => [$columnName['CHANGE24H_UP50_EMA'] => $firstEma]
                    ]);

                    print_r($item);
                    echo $firstEma;

                    $startObjectIndex[$index]->{$columnName['CHANGE24H_UP50_EMA']} = $firstEma;
                }
            }
        }

        if (!isset($startObjectIndex[$index])) return Reply::make(false, 'Can not get start object');

        $firstEma = $startObjectIndex[$index]->{$columnName['CHANGE24H_UP50_EMA']};
        $startPoint = $startObjectIndex[$index]->{CHANGE24H_TIME};

        if (!$firstEma > 0) return Reply::make(false, 'Can not caculate EMA');

        $K = 2 / ($N + 1);

        $periodEma = $firstEma;

        while (true) {
            $restPoints = $model->read([[[CHANGE24H_TIME, '>', $startPoint], [$columnName['CHANGE24H_UP50_EMA'], '=', null]]], function ($db) use ($columnName) {
                $db->orderBy(CHANGE24H_TIME, 'ASC');
            }, true, [CHANGE24H_ID, CHANGE24H_TIME, $columnName['CHANGE24H_UP50_EMA'], CHANGE24H_UP50]);

            if (!$restPoints['result']) return $restPoints;

            $restPoints = $restPoints['data'];

            foreach ($restPoints as $restPoint) {
                $ema = $periodEma * (1 - $K) + $restPoint->{CHANGE24H_UP50} * $K;


                $result = $model->edit([
                    DATA_KEY => [[[CHANGE24H_ID, '=', $restPoint->{CHANGE24H_ID}]]],
                    DATA_EDITOR => [$columnName['CHANGE24H_UP50_EMA'] => $ema]
                ]);
                if (!$result['result']) return $result;
                $restPoint->{$columnName['CHANGE24H_UP50_EMA']} = $ema;

                $periodEma = $ema;
                $startObjectIndex[$index] = $restPoint;
                $startPoint = $startObjectIndex[$index]->{CHANGE24H_TIME};
            }

            if (count($restPoints) <= 5000) break;
        }

        return Reply::make(true, 'success');
    }
}
